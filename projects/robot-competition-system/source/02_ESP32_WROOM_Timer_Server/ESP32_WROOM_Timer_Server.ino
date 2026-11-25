/*
  ESP32 WROOM 32 - Competition Web Timer
  -------------------------------------------
  GPIO4  : pressure sensor input A
  GPIO17 : pressure sensor input B
  GPIO18 : STOP button, connect to GND
  GPIO19 : RESET button, connect to GND

  IMPORTANT: GPIO6-GPIO11 are reserved for the ESP32 flash.
  Do not connect buttons or sensors to those pins.

  This WROOM board receives a ROUTE event from the RFID sender, starts the timer,
  and serves the HTML web page.

  Both installed pressure sensors use polarity-independent edge detection.
  For analog pressure sensors, enable PRESSURE_ANALOG_MODE.
*/

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <esp_arduino_version.h>
#include <cstring>
#include "web_page.h"

// ===================== Wi-Fi =====================
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// ===================== Pins =====================
constexpr uint8_t PRESSURE_D4_PIN = 4;
constexpr uint8_t PRESSURE_D17_PIN = 17;
constexpr uint8_t STOP_BUTTON_PIN = 18;
constexpr uint8_t RESET_BUTTON_PIN = 19;

constexpr bool USE_PRESSURE_D4 = true;
constexpr bool USE_PRESSURE_D17 = true;
constexpr bool PRESSURE_ANALOG_MODE = false;

// Digital mode: any stable level change triggers the stop. This supports
// both active-high and active-low sensor modules.
constexpr bool PRESSURE_TRIGGER_HIGH = true;
constexpr int PRESSURE_THRESHOLD = 1500;
constexpr uint32_t PRESSURE_DEBOUNCE_MS = 30;

// ===================== ESP-NOW =====================
constexpr uint32_t PACKET_MAGIC = 0x5A4F4E45;
constexpr uint8_t PROTOCOL_VERSION = 1;
constexpr uint8_t EVENT_CARD_ROUTE = 2;
constexpr uint8_t CMD_MOVE_180 = 1;
constexpr uint8_t CMD_SERVO_RESET = 2;

struct __attribute__((packed)) CardEventPacket {
  uint32_t magic;
  uint8_t version;
  uint8_t eventType;
  uint16_t sequence;
  char route[8];
};
static_assert(sizeof(CardEventPacket) == 16, "CardEventPacket must be 16 bytes");

struct __attribute__((packed)) CommandPacket {
  uint32_t magic;
  uint8_t version;
  uint8_t command;
  uint16_t sequence;
};
static_assert(sizeof(CommandPacket) == 8, "CommandPacket must be 8 bytes");

enum class TimerState : uint8_t {
  WAITING,
  RUNNING,
  STOPPED
};

WebServer server(80);

TimerState timerState = TimerState::WAITING;
String currentRoute;
uint32_t startedAtMs = 0;
uint32_t finalElapsedMs = 0;
uint16_t cycleSequence = 0;

volatile bool cardEventPending = false;
volatile uint16_t pendingSequence = 0;
char pendingRoute[8] = {0};

bool lastStopPressed = false;
bool lastResetPressed = false;
uint8_t pressureStableState = 0;
uint8_t pressureCandidateState = 0;
uint32_t pressureCandidateSinceMs = 0;
bool pressureCandidateActive = false;
String stopReason = "none";

#if ESP_ARDUINO_VERSION_MAJOR >= 3
void onDataRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  (void)info;
#else
void onDataRecv(const uint8_t *macAddr, const uint8_t *data, int len) {
  (void)macAddr;
#endif
  if (len != static_cast<int>(sizeof(CardEventPacket))) return;

  CardEventPacket packet{};
  memcpy(&packet, data, sizeof(packet));

  if (packet.magic != PACKET_MAGIC ||
      packet.version != PROTOCOL_VERSION ||
      packet.eventType != EVENT_CARD_ROUTE) {
    return;
  }

  packet.route[sizeof(packet.route) - 1] = '\0';
  strncpy(pendingRoute, packet.route, sizeof(pendingRoute) - 1);
  pendingRoute[sizeof(pendingRoute) - 1] = '\0';
  pendingSequence = packet.sequence;
  cardEventPending = true;
}

void configureInputs() {
  if (USE_PRESSURE_D4) {
    pinMode(PRESSURE_D4_PIN, PRESSURE_ANALOG_MODE ? INPUT : INPUT_PULLUP);
  } else {
    pinMode(PRESSURE_D4_PIN, INPUT);
  }

  if (USE_PRESSURE_D17) {
    pinMode(PRESSURE_D17_PIN, PRESSURE_ANALOG_MODE ? INPUT : INPUT_PULLUP);
  } else {
    pinMode(PRESSURE_D17_PIN, INPUT);
  }
  pinMode(STOP_BUTTON_PIN, INPUT_PULLUP);
  pinMode(RESET_BUTTON_PIN, INPUT_PULLUP);
  lastStopPressed = (digitalRead(STOP_BUTTON_PIN) == LOW);
  lastResetPressed = (digitalRead(RESET_BUTTON_PIN) == LOW);
}

uint8_t readPressureState() {
  uint8_t state = 0;

  if (USE_PRESSURE_D4) {
    const bool active = PRESSURE_ANALOG_MODE
        ? (PRESSURE_TRIGGER_HIGH ? analogRead(PRESSURE_D4_PIN) >= PRESSURE_THRESHOLD
                                 : analogRead(PRESSURE_D4_PIN) <= PRESSURE_THRESHOLD)
        : (digitalRead(PRESSURE_D4_PIN) == HIGH);
    if (active) state |= 0x01;
  }

  if (USE_PRESSURE_D17) {
    const bool active = PRESSURE_ANALOG_MODE
        ? (PRESSURE_TRIGGER_HIGH ? analogRead(PRESSURE_D17_PIN) >= PRESSURE_THRESHOLD
                                 : analogRead(PRESSURE_D17_PIN) <= PRESSURE_THRESHOLD)
        : (digitalRead(PRESSURE_D17_PIN) == HIGH);
    if (active) state |= 0x02;
  }

  return state;
}

void capturePressureBaseline() {
  pressureStableState = readPressureState();
  pressureCandidateState = pressureStableState;
  pressureCandidateSinceMs = millis();
  pressureCandidateActive = false;
}

uint32_t elapsedMs() {
  if (timerState == TimerState::RUNNING) return millis() - startedAtMs;
  if (timerState == TimerState::STOPPED) return finalElapsedMs;
  return 0;
}

void startTimerFromCard(const char *route, uint16_t sequence) {
  if (timerState != TimerState::WAITING) {
    Serial.println("Card event ignored: press GPIO19 reset button first.");
    return;
  }

  currentRoute = route;
  currentRoute.trim();
  currentRoute.toUpperCase();
  if (currentRoute.length() == 0) currentRoute = "?";

  cycleSequence = sequence;
  startedAtMs = millis();
  finalElapsedMs = 0;
  stopReason = "none";
  capturePressureBaseline();
  timerState = TimerState::RUNNING;
  Serial.printf("Route %s started. sequence=%u\n",
                currentRoute.c_str(),
                static_cast<unsigned>(sequence));
}

void stopTimer(const char *reason = "unknown") {
  if (timerState != TimerState::RUNNING) return;
  finalElapsedMs = millis() - startedAtMs;
  stopReason = reason;
  timerState = TimerState::STOPPED;
  Serial.printf("Timer stopped at %lu ms\n",
                static_cast<unsigned long>(finalElapsedMs));
}

void sendMoveTestPacket() {
  CommandPacket packet{};
  packet.magic = PACKET_MAGIC;
  packet.version = PROTOCOL_VERSION;
  packet.command = CMD_MOVE_180;
  packet.sequence = ++cycleSequence;

  uint8_t broadcastMac[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
  const esp_err_t result = esp_now_send(
      broadcastMac,
      reinterpret_cast<const uint8_t *>(&packet),
      sizeof(packet));

  if (result == ESP_OK) {
    Serial.println("MOVE_180 test broadcast sent.");
  } else {
    Serial.printf("MOVE_180 send failed: %s\n", esp_err_to_name(result));
  }
}

void sendResetPacket() {
  CommandPacket packet{};
  packet.magic = PACKET_MAGIC;
  packet.version = PROTOCOL_VERSION;
  packet.command = CMD_SERVO_RESET;
  packet.sequence = ++cycleSequence;

  uint8_t broadcastMac[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
  const esp_err_t result = esp_now_send(
      broadcastMac,
      reinterpret_cast<const uint8_t *>(&packet),
      sizeof(packet));

  if (result == ESP_OK) {
    Serial.println("RESET broadcast sent to sender and servo receiver.");
  } else {
    Serial.printf("RESET send failed: %s\n", esp_err_to_name(result));
  }
}

void resetSystem() {
  timerState = TimerState::WAITING;
  currentRoute = "";
  startedAtMs = 0;
  finalElapsedMs = 0;
  stopReason = "none";
  capturePressureBaseline();
  cardEventPending = false;
  sendResetPacket();
  Serial.println("System reset. Waiting for next card.");
}

void handleButtonsAndPressure() {
  const bool stopPressed = (digitalRead(STOP_BUTTON_PIN) == LOW);
  if (stopPressed && !lastStopPressed && timerState == TimerState::RUNNING) {
    Serial.println("STOP triggered by GPIO18 button.");
    stopTimer("button");
  }
  lastStopPressed = stopPressed;

  const bool resetPressed = (digitalRead(RESET_BUTTON_PIN) == LOW);
  if (resetPressed && !lastResetPressed) {
    resetSystem();
  }
  lastResetPressed = resetPressed;

  const uint8_t pressureNow = readPressureState();
  if (timerState == TimerState::RUNNING) {
    if (pressureNow != pressureStableState) {
      if (!pressureCandidateActive || pressureNow != pressureCandidateState) {
        pressureCandidateActive = true;
        pressureCandidateState = pressureNow;
        pressureCandidateSinceMs = millis();
      } else if (static_cast<uint32_t>(millis() - pressureCandidateSinceMs) >=
                 PRESSURE_DEBOUNCE_MS) {
        Serial.printf("STOP triggered by pressure change: D4=%d D17=%d baseline=%u current=%u\n",
                      digitalRead(PRESSURE_D4_PIN),
                      digitalRead(PRESSURE_D17_PIN),
                      static_cast<unsigned>(pressureStableState),
                      static_cast<unsigned>(pressureNow));
        stopTimer("pressure");
        pressureStableState = pressureNow;
        pressureCandidateActive = false;
      }
    } else {
      pressureCandidateActive = false;
    }
  } else {
    pressureCandidateActive = false;
    pressureStableState = pressureNow;
  }
}

const char* stateName() {
  switch (timerState) {
    case TimerState::RUNNING: return "running";
    case TimerState::STOPPED: return "stopped";
    default: return "waiting";
  }
}

void handleStatus() {
  String json = "{";
  json += "\"state\":\"";
  json += stateName();
  json += "\",\"route\":\"";
  json += currentRoute;
  json += "\",\"elapsed\":";
  json += String(elapsedMs());
  json += ",\"final\":";
  json += String(timerState == TimerState::STOPPED ? finalElapsedMs : 0);
  json += ",\"sequence\":";
  json += String(cycleSequence);
  json += ",\"stopReason\":\"";
  json += stopReason;
  json += "\",\"d4\":";
  json += String(digitalRead(PRESSURE_D4_PIN));
  json += ",\"d17\":";
  json += String(digitalRead(PRESSURE_D17_PIN));
  json += ",\"stopPin\":";
  json += String(digitalRead(STOP_BUTTON_PIN));
  json += ",\"resetPin\":";
  json += String(digitalRead(RESET_BUTTON_PIN));
  json += ",\"pressureState\":";
  json += String(readPressureState());
  json += ",\"pressureBaseline\":";
  json += String(pressureStableState);
  json += "}";
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "application/json", json);
}

void handleStopRequest() {
  stopTimer("web");
  server.send(200, "application/json", "{\"ok\":true}");
}

void handleResetRequest() {
  resetSystem();
  server.send(200, "application/json", "{\"ok\":true}");
}

void handleRoot() {
  server.sendHeader("Cache-Control", "no-store");
  server.send_P(200, "text/html; charset=utf-8", WEB_PAGE_HTML);
}

void handleNotFound() {
  server.send(404, "text/plain; charset=utf-8", "Not found");
}

bool connectWifi() {
  WiFi.mode(WIFI_AP_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  const uint32_t startMs = millis();
  while (WiFi.status() != WL_CONNECTED &&
         static_cast<uint32_t>(millis() - startMs) < 20000) {
    delay(250);
    Serial.print('.');
  }
  Serial.println();
  return WiFi.status() == WL_CONNECTED;
}

bool initEspNow() {
  if (esp_now_init() != ESP_OK) return false;
  esp_now_register_recv_cb(onDataRecv);

  uint8_t broadcastMac[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
  esp_now_peer_info_t peerInfo{};
  memcpy(peerInfo.peer_addr, broadcastMac, sizeof(broadcastMac));
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  peerInfo.ifidx = (WiFi.status() == WL_CONNECTED) ? WIFI_IF_STA : WIFI_IF_AP;
  const esp_err_t result = esp_now_add_peer(&peerInfo);
  return result == ESP_OK || result == ESP_ERR_ESPNOW_EXIST;
}

void handleSerialTestCommands() {
  while (Serial.available() > 0) {
    const char command = static_cast<char>(toupper(Serial.read()));
    if (command == 'T') {
      if (timerState == TimerState::WAITING) {
        startTimerFromCard("T", 999);
      } else {
        Serial.println("Serial T ignored: press R first.");
      }
    } else if (command == 'S') {
      stopTimer("serial");
    } else if (command == 'R') {
      resetSystem();
    } else if (command == 'O') {
      sendMoveTestPacket();
    }
  }
}

bool startLocalAccessPoint(uint8_t channel) {
  IPAddress apIp(192, 168, 4, 1);
  IPAddress apGateway(192, 168, 4, 1);
  IPAddress apSubnet(255, 255, 255, 0);
  WiFi.softAPConfig(apIp, apGateway, apSubnet);

  const uint8_t apChannel = (channel == 0) ? 6 : channel;
  const bool apStarted = WiFi.softAP(
      "RobotTimer", "12345678", apChannel, false, 4);

  Serial.printf("softAP result=%s mode=%d IP=%s channel=%u\n",
                apStarted ? "OK" : "FAIL",
                static_cast<int>(WiFi.getMode()),
                WiFi.softAPIP().toString().c_str(),
                static_cast<unsigned>(apChannel));
  Serial.printf("Local AP: SSID=RobotTimer password=12345678 url=http://%s/\n",
                WiFi.softAPIP().toString().c_str());
  return apStarted;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  configureInputs();
  capturePressureBaseline();

  Serial.println();
  Serial.println("ESP32 WROOM 32 - 30th Anniversary Robot Challenge Timer");
  Serial.println("GPIO4/GPIO17 pressure, GPIO18 stop, GPIO19 reset");
  Serial.printf("Raw inputs (idle expected): GPIO4=%d GPIO17=%d GPIO18=%d GPIO19=%d\n",
                digitalRead(PRESSURE_D4_PIN),
                digitalRead(PRESSURE_D17_PIN),
                digitalRead(STOP_BUTTON_PIN),
                digitalRead(RESET_BUTTON_PIN));

  const bool wifiConnected = connectWifi();
  if (!wifiConnected) {
    Serial.println("Wi-Fi failed. Scanning nearby 2.4 GHz networks...");
    const int networkCount = WiFi.scanNetworks();
    for (int i = 0; i < networkCount; ++i) {
      Serial.printf("  SSID=%s RSSI=%d channel=%d encrypted=%d\n",
                    WiFi.SSID(i).c_str(), WiFi.RSSI(i), WiFi.channel(i),
                    WiFi.encryptionType(i) != WIFI_AUTH_OPEN);
    }

    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    delay(300);
    WiFi.mode(WIFI_AP);
    delay(200);
    startLocalAccessPoint(6);
  } else {
    Serial.printf("Wi-Fi connected. IP=%s channel=%d\n",
                  WiFi.localIP().toString().c_str(), WiFi.channel());
    startLocalAccessPoint(WiFi.channel());
    if (MDNS.begin("robot-timer")) {
      Serial.println("mDNS: http://robot-timer.local/");
    }
  }

  if (!initEspNow()) {
    Serial.println("FAIL: ESP-NOW init failed.");
  }

  server.on("/", HTTP_GET, handleRoot);
  server.on("/status", HTTP_GET, handleStatus);
  server.on("/stop", HTTP_POST, handleStopRequest);
  server.on("/reset", HTTP_POST, handleResetRequest);
  server.onNotFound(handleNotFound);
  server.begin();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("Web page via router: http://%s/\n", WiFi.localIP().toString().c_str());
  }
  Serial.printf("Web page via local AP: http://%s/\n", WiFi.softAPIP().toString().c_str());
  Serial.println("Waiting for card route event...");
  Serial.println("Serial test: T=start, S=stop, R=reset, O=test servo 180");
}

void loop() {
  if (cardEventPending) {
    cardEventPending = false;
    startTimerFromCard(pendingRoute, pendingSequence);
  }

  handleButtonsAndPressure();
  handleSerialTestCommands();
  server.handleClient();
  delay(5);
}
