/*
  ESP32-S3 RC522 -> Google Sheet -> ESP-NOW -> XIAO ESP32C6
  ---------------------------------------------------------
  RC522 wiring (original mapping):
    SDA/SS -> D10 / GPIO10
    SCK    -> D13 / GPIO13
    MOSI   -> D11 / GPIO11
    MISO   -> D12 / GPIO12
    RST    -> D9  / GPIO9
    3.3V   -> 3V3
    GND    -> GND

  Google Sheet:
    File: robot competition result
    Allowed card numbers: CARD sheet column A, starting A2
    Results appended to: result sheet

  Behaviour:
    - Fetch allowed card numbers from Google Sheet at boot.
    - Refresh every 5 minutes while idle.
    - Tap allowed card -> send route to ESP32-WROOM immediately -> wait 5 seconds -> ESP-NOW MOVE_180 to XIAO ESP32-C6 -> servo 0..180 for 35 seconds.
    - Accepted result is appended to Google Sheet.
    - If a route cannot be loaded, the card is rejected. Never send ? as a route.

  Required libraries:
    - MFRC522
  Built-in:
    - WiFi, HTTPClient, WiFiClientSecure, ESP-NOW

  IMPORTANT:
    - Both sender and receiver must connect to the same 2.4 GHz Wi-Fi AP so their
      ESP-NOW channels match.
    - Fill WIFI_SSID, WIFI_PASSWORD, SHEETS_WEB_APP_URL and API_TOKEN.
*/

#include <Arduino.h>
#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <esp_arduino_version.h>
#include <esp_idf_version.h>
#include <cstring>
#include <vector>
#include <algorithm>
#include <cctype>
#include <cstdio>

// ===================== USER SETTINGS =====================
const char *WIFI_SSID = "YOUR_WIFI_SSID";
const char *WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Google Apps Script Web App URL, ending in /exec. Replace this if redeployed.
const char *SHEETS_WEB_APP_URL = "YOUR_APPS_SCRIPT_WEB_APP_URL";
const char *API_TOKEN = "CHANGE_ME_RANDOM_TOKEN";  // Must match RobotCompetitionSheet.gs

constexpr uint8_t RFID_SDA_PIN = 10;
constexpr uint8_t RFID_SCK_PIN = 13;
constexpr uint8_t RFID_MOSI_PIN = 11;
constexpr uint8_t RFID_MISO_PIN = 12;
constexpr uint8_t RFID_RST_PIN = 9;

constexpr uint32_t CARD_DELAY_MS = 5000;
constexpr uint32_t SERVO_ACTIVE_MS = 35000;
constexpr uint32_t SEND_TIMEOUT_MS = 1500;
constexpr uint32_t SEND_RETRY_MS = 1000;
constexpr uint32_t CARD_REFRESH_MS = 300000;
constexpr uint32_t WIFI_CONNECT_TIMEOUT_MS = 15000;
constexpr uint8_t FALLBACK_ESPNOW_CHANNEL = 1;

constexpr uint32_t PACKET_MAGIC = 0x5A4F4E45;
constexpr uint8_t PROTOCOL_VERSION = 1;
constexpr uint8_t CMD_MOVE_180 = 1;
constexpr uint8_t CMD_SERVO_RESET = 2;
constexpr uint8_t EVENT_CARD_ROUTE = 2;

struct __attribute__((packed)) CommandPacket {
  uint32_t magic;
  uint8_t version;
  uint8_t command;
  uint16_t sequence;
};
static_assert(sizeof(CommandPacket) == 8, "CommandPacket must be 8 bytes");

struct __attribute__((packed)) CardEventPacket {
  uint32_t magic;
  uint8_t version;
  uint8_t eventType;
  uint16_t sequence;
  char route[8];
};
static_assert(sizeof(CardEventPacket) == 16, "CardEventPacket must be 16 bytes");

struct CardMapping {
  String uid;
  String route;
};

MFRC522 rfid(RFID_SDA_PIN, RFID_RST_PIN);

enum class SenderState : uint8_t {
  READY,
  WAIT_BEFORE_SEND,
  SENDING,
  COOLDOWN
};

SenderState state = SenderState::READY;
uint32_t deadlineMs = 0;
uint32_t sendStartedMs = 0;
uint32_t lastCardRefreshMs = 0;
uint16_t nextSequence = 1;
volatile bool sendFinished = false;
volatile bool sendSucceeded = false;
volatile bool systemResetPending = false;
std::vector<CardMapping> cardMap;
String pendingUid;
String pendingRoute;

String normalizeUidText(const String &input) {
  String hex;
  for (size_t i = 0; i < input.length(); ++i) {
    char c = input[i];
    if ((c >= '0' && c <= '9') || (c >= 'A' && c <= 'F') || (c >= 'a' && c <= 'f')) {
      hex += static_cast<char>(toupper(c));
    }
  }

  if (hex.length() != 8 && hex.length() != 14) return "";

  String result;
  for (size_t i = 0; i < hex.length(); i += 2) {
    if (i > 0) result += ':';
    result += hex.substring(i, i + 2);
  }
  return result;
}

String uidToString(const uint8_t *uid, uint8_t length) {
  String out;
  char pair[3];
  for (uint8_t i = 0; i < length; ++i) {
    snprintf(pair, sizeof(pair), "%02X", uid[i]);
    if (i > 0) out += ':';
    out += pair;
  }
  return out;
}

String normalizeRouteText(const String &input) {
  String result;
  for (size_t i = 0; i < input.length(); ++i) {
    char c = static_cast<char>(toupper(input[i]));
    if ((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '-' || c == '_') {
      result += c;
      if (result.length() >= 7) break;
    }
  }
  return result;
}

String routeForCard(const String &uid) {
  for (const CardMapping &entry : cardMap) {
    if (entry.uid == uid) return entry.route;
  }
  return "";
}

bool addCardMapping(const String &uidText, const String &routeText) {
  const String normalizedUid = normalizeUidText(uidText);
  if (normalizedUid.length() == 0) return false;

  String normalizedRoute = normalizeRouteText(routeText);
  if (normalizedRoute.length() == 0) return false;

  for (CardMapping &entry : cardMap) {
    if (entry.uid == normalizedUid) {
      entry.route = normalizedRoute;
      return true;
    }
  }

  cardMap.push_back({ normalizedUid, normalizedRoute });
  return true;
}

void loadFallbackCards() {
  // Never send "?" as a route. A valid route must come from the Google Sheet.
  cardMap.clear();
}

String urlEncode(const String &input) {
  const char *hex = "0123456789ABCDEF";
  String out;
  for (size_t i = 0; i < input.length(); ++i) {
    uint8_t c = static_cast<uint8_t>(input[i]);
    if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '-' || c == '_' || c == '.' || c == '~') {
      out += static_cast<char>(c);
    } else {
      out += '%';
      out += hex[(c >> 4) & 0x0F];
      out += hex[c & 0x0F];
    }
  }
  return out;
}

String makeRequestUrl(const String &action, const String &extra = "") {
  String url = String(SHEETS_WEB_APP_URL);
  url += "?token=";
  url += urlEncode(String(API_TOKEN));
  url += "&action=";
  url += urlEncode(action);
  url += extra;
  return url;
}

bool httpGet(const String &url, String &responseBody) {
  if (WiFi.status() != WL_CONNECTED) return false;

  WiFiClientSecure client;
  client.setInsecure();  // HTTPS encryption without certificate validation.

  HTTPClient http;
  http.setTimeout(8000);
  http.setFollowRedirects(HTTPC_STRICT_FOLLOW_REDIRECTS);

  if (!http.begin(client, url)) {
    Serial.println("HTTP begin failed");
    return false;
  }

  const int statusCode = http.GET();
  responseBody = http.getString();
  http.end();

  if (statusCode != HTTP_CODE_OK) {
    Serial.printf("HTTP status: %d\n", statusCode);
    return false;
  }
  return true;
}

bool fetchCardsFromSheet() {
  String body;
  if (!httpGet(makeRequestUrl("cards"), body)) return false;

  body.trim();
  if (body.length() == 0) {
    Serial.println("Sheet returned no card mappings.");
    return false;
  }

  std::vector<CardMapping> newCards;
  int start = 0;
  while (start < static_cast<int>(body.length())) {
    int end = body.indexOf('\n', start);
    if (end < 0) end = body.length();

    String line = body.substring(start, end);
    line.trim();

    const int separator = line.indexOf('|');
    const String uidPart = separator >= 0 ? line.substring(0, separator) : line;
    const String routePart = separator >= 0 ? line.substring(separator + 1) : "?";
    const String normalizedUid = normalizeUidText(uidPart);
    String normalizedRoute = normalizeRouteText(routePart);
    if (normalizedRoute.length() == 0) return false;

    if (normalizedUid.length() > 0) {
      bool exists = false;
      for (const CardMapping &entry : newCards) {
        if (entry.uid == normalizedUid) {
          exists = true;
          break;
        }
      }
      if (!exists) newCards.push_back({ normalizedUid, normalizedRoute });
    }
    start = end + 1;
  }

  if (newCards.empty()) return false;
  cardMap.swap(newCards);
  return true;
}

bool logCardEvent(const String &uid, const String &result, const String &note) {
  String extra = "&uid=";
  extra += urlEncode(uid);
  extra += "&result=";
  extra += urlEncode(result);
  extra += "&note=";
  extra += urlEncode(note);

  String body;
  const bool ok = httpGet(makeRequestUrl("log", extra), body);
  if (ok) {
    Serial.printf("Sheet log: %s\n", body.c_str());
  } else {
    Serial.println("Sheet log failed.");
  }
  return ok;
}

bool connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  const uint32_t startMs = millis();
  while (WiFi.status() != WL_CONNECTED && static_cast<uint32_t>(millis() - startMs) < WIFI_CONNECT_TIMEOUT_MS) {
    delay(250);
    Serial.print('.');
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("Wi-Fi connected. Channel=%d\n", WiFi.channel());
    return true;
  }

  Serial.println("Wi-Fi failed. Using fallback ESP-NOW channel 1.");
  WiFi.disconnect(false, false);
  delay(100);
  esp_wifi_set_channel(FALLBACK_ESPNOW_CHANNEL, WIFI_SECOND_CHAN_NONE);
  return false;
}

#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 5, 0)
void onDataSent(const esp_now_send_info_t *txInfo, esp_now_send_status_t status) {
  (void)txInfo;
#else
void onDataSent(const uint8_t *macAddr, esp_now_send_status_t status) {
  (void)macAddr;
#endif
  sendSucceeded = (status == ESP_NOW_SEND_SUCCESS);
  sendFinished = true;
}

#if ESP_ARDUINO_VERSION_MAJOR >= 3
void onDataRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  (void)info;
#else
void onDataRecv(const uint8_t *macAddr, const uint8_t *data, int len) {
  (void)macAddr;
#endif
  if (len != static_cast<int>(sizeof(CommandPacket))) return;

  CommandPacket packet{};
  memcpy(&packet, data, sizeof(packet));
  if (packet.magic == PACKET_MAGIC && packet.version == PROTOCOL_VERSION && packet.command == CMD_SERVO_RESET) {
    systemResetPending = true;
  }
}

bool beginEspNow() {
  if (esp_now_init() != ESP_OK) return false;
  esp_now_register_send_cb(onDataSent);
  esp_now_register_recv_cb(onDataRecv);

  uint8_t broadcastMac[6] = { 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF };
  esp_now_peer_info_t peerInfo{};
  std::memcpy(peerInfo.peer_addr, broadcastMac, sizeof(broadcastMac));
  peerInfo.channel = 0;  // current Wi-Fi channel
  peerInfo.encrypt = false;

  const esp_err_t result = esp_now_add_peer(&peerInfo);
  return result == ESP_OK || result == ESP_ERR_ESPNOW_EXIST;
}

void sendCardEvent(uint32_t now) {
  (void)now;
  CardEventPacket packet{};
  packet.magic = PACKET_MAGIC;
  packet.version = PROTOCOL_VERSION;
  packet.eventType = EVENT_CARD_ROUTE;
  packet.sequence = nextSequence++;

  size_t routeLength = pendingRoute.length();
  if (routeLength > sizeof(packet.route) - 1) routeLength = sizeof(packet.route) - 1;
  memcpy(packet.route, pendingRoute.c_str(), routeLength);
  packet.route[routeLength] = '\0';

  uint8_t broadcastMac[6] = { 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF };
  const esp_err_t result = esp_now_send(
    broadcastMac,
    reinterpret_cast<const uint8_t *>(&packet),
    sizeof(packet));

  if (result == ESP_OK) {
    Serial.printf("C3 card event sent: route=%s\n", packet.route);
  } else {
    Serial.printf("C3 card event failed: %s\n", esp_err_to_name(result));
  }
}

void queueMoveCommand(uint32_t now) {
  const uint16_t sequence = nextSequence++;
  CommandPacket packet{};
  packet.magic = PACKET_MAGIC;
  packet.version = PROTOCOL_VERSION;
  packet.command = CMD_MOVE_180;
  packet.sequence = sequence;

  sendFinished = false;
  sendSucceeded = false;
  sendStartedMs = now;

  uint8_t broadcastMac[6] = { 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF };
  const esp_err_t result = esp_now_send(
    broadcastMac,
    reinterpret_cast<const uint8_t *>(&packet),
    sizeof(packet));

  if (result != ESP_OK) {
    Serial.printf("ESP-NOW queue failed: %s\n", esp_err_to_name(result));
    sendFinished = true;
    sendSucceeded = false;
  } else {
    Serial.printf("ESP-NOW command queued, sequence=%u\n",
                  static_cast<unsigned>(sequence));
  }
}

void refreshCardsIfDue(uint32_t now) {
  if (static_cast<uint32_t>(now - lastCardRefreshMs) < CARD_REFRESH_MS) return;
  lastCardRefreshMs = now;

  if (WiFi.status() != WL_CONNECTED) {
    WiFi.reconnect();
    return;
  }

  if (fetchCardsFromSheet()) {
    Serial.printf("Card mappings loaded from Google Sheet: %u\n",
                  static_cast<unsigned>(cardMap.size()));
  } else {
    Serial.println("Google Sheet refresh failed; keeping current mappings.");
  }
}

void pollCard(uint32_t now) {
  if (!rfid.PICC_IsNewCardPresent()) return;
  if (!rfid.PICC_ReadCardSerial()) return;

  const String uid = uidToString(rfid.uid.uidByte, rfid.uid.size);
  Serial.print("Card UID: ");
  Serial.println(uid);

  const String route = routeForCard(uid);
  if (route.length() > 0) {
    pendingUid = uid;
    pendingRoute = route;

    // Send the route immediately so the HTML timer starts on card tap.
    sendCardEvent(now);

    state = SenderState::WAIT_BEFORE_SEND;
    deadlineMs = now + CARD_DELAY_MS;
    Serial.printf("APPROVED: route=%s, waiting 5 seconds.\n", route.c_str());
  } else {
    Serial.println("DENIED: UID not in sheet/fallback map.");
    logCardEvent(uid, "REJECTED", "not_in_card_sheet");
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("ESP32-S3 RC522 Google-Sheet Sender");

  loadFallbackCards();

  const bool wifiOk = connectWifi();
  if (wifiOk) {
    if (fetchCardsFromSheet()) {
      Serial.printf("Initial card mappings from sheet: %u\n",
                    static_cast<unsigned>(cardMap.size()));
    } else {
      Serial.println("Sheet fetch failed; using three fallback mappings.");
    }
  } else {
    Serial.println("Offline mode: using three fallback mappings.");
  }
  lastCardRefreshMs = millis();

  SPI.begin(RFID_SCK_PIN, RFID_MISO_PIN, RFID_MOSI_PIN, RFID_SDA_PIN);
  pinMode(RFID_SDA_PIN, OUTPUT);
  digitalWrite(RFID_SDA_PIN, HIGH);
  rfid.PCD_Init();
  delay(50);

  const uint8_t version = rfid.PCD_ReadRegister(MFRC522::VersionReg);
  Serial.printf("RC522 VersionReg=0x%02X\n", static_cast<unsigned>(version));

  if (!beginEspNow()) {
    Serial.println("ESP-NOW startup failed.");
    for (;;) delay(1000);
  }

  Serial.printf("MAC: %s\n", WiFi.macAddress().c_str());
  Serial.println("Ready. Tap a card.");
}

void loop() {
  const uint32_t now = millis();

  if (systemResetPending) {
    systemResetPending = false;
    state = SenderState::READY;
    deadlineMs = 0;
    pendingUid = "";
    pendingRoute = "";
    Serial.println("SYSTEM RESET received from C3. Sender ready.");
  }

  switch (state) {
    case SenderState::READY:
      refreshCardsIfDue(now);
      pollCard(now);
      break;

    case SenderState::WAIT_BEFORE_SEND:
      if (static_cast<int32_t>(now - deadlineMs) >= 0) {
        state = SenderState::SENDING;
        queueMoveCommand(now);
      }
      break;

    case SenderState::SENDING:
      if (sendFinished) {
        if (sendSucceeded) {
          Serial.println("ESP-NOW send OK.");
          state = SenderState::COOLDOWN;
          deadlineMs = millis() + SERVO_ACTIVE_MS;
          logCardEvent(pendingUid, "ACCEPTED_180", String("route_") + pendingRoute + ",servo_command_sent");
        } else {
          Serial.println("ESP-NOW send failed; retry in 1 second.");
          state = SenderState::WAIT_BEFORE_SEND;
          deadlineMs = millis() + SEND_RETRY_MS;
        }
      } else if (static_cast<uint32_t>(millis() - sendStartedMs) >= SEND_TIMEOUT_MS) {
        sendFinished = true;
        sendSucceeded = false;
      }
      break;

    case SenderState::COOLDOWN:
      if (static_cast<int32_t>(now - deadlineMs) >= 0) {
        state = SenderState::READY;
        Serial.println("35-second cycle complete. Ready for next card.");
      }
      break;
  }

  delay(10);
}
