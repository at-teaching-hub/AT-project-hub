/*
  Seeed XIAO ESP32C6 Servo Receiver - 35 seconds
  ------------------------------------------------
  D9 / GPIO20 -> Servo Signal
  XIAO GND -> external 5V GND
  Servo V+ -> external 5V positive
  Servo GND -> external 5V negative

  收到 ESP-NOW:
    0 -> 180 degrees
    Hold 35 seconds
    Return to 0 degrees

  Both sender and receiver should connect to the same 2.4 GHz Wi-Fi AP.
  This keeps the ESP-NOW channel synchronized.
*/

#include <Arduino.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <esp_arduino_version.h>

// ===================== USER SETTINGS =====================
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

constexpr uint8_t SERVO_PIN = 20;       // XIAO ESP32C6 D9
constexpr uint8_t USER_LED_PIN = 15;    // Active low
constexpr uint8_t SERVO_CLOSED_ANGLE = 0;
constexpr uint8_t SERVO_OPEN_ANGLE = 180;
constexpr uint32_t SERVO_ACTIVE_MS = 35000;
constexpr uint8_t ANGLE_STEP = 1;
constexpr uint16_t STEP_DELAY_MS = 10;

constexpr uint32_t SERVO_FREQ_HZ = 50;
constexpr uint8_t SERVO_RESOLUTION_BITS = 14;
constexpr uint32_t SERVO_PERIOD_US = 20000;
constexpr uint16_t SERVO_MIN_PULSE_US = 1000;
constexpr uint16_t SERVO_MAX_PULSE_US = 2000;

constexpr uint8_t FALLBACK_ESPNOW_CHANNEL = 1;
constexpr uint32_t WIFI_CONNECT_TIMEOUT_MS = 15000;

constexpr uint32_t PACKET_MAGIC = 0x5A4F4E45;
constexpr uint8_t PROTOCOL_VERSION = 1;
constexpr uint8_t CMD_MOVE_180 = 1;
constexpr uint8_t CMD_SERVO_RESET = 2;

#if ESP_ARDUINO_VERSION_MAJOR < 3
constexpr uint8_t SERVO_LEDC_CHANNEL = 0;
#endif

struct __attribute__((packed)) CommandPacket {
  uint32_t magic;
  uint8_t version;
  uint8_t command;
  uint16_t sequence;
};
static_assert(sizeof(CommandPacket) == 8, "CommandPacket must be 8 bytes");

volatile bool commandPending = false;
volatile bool resetPending = false;
volatile uint16_t receivedSequence = 0;
uint8_t currentAngle = SERVO_CLOSED_ANGLE;
bool servoActive = false;
uint32_t activeUntilMs = 0;

uint32_t angleToDuty(uint8_t angle) {
  if (angle > 180) angle = 180;
  const uint32_t pulseUs =
      SERVO_MIN_PULSE_US +
      (static_cast<uint32_t>(SERVO_MAX_PULSE_US - SERVO_MIN_PULSE_US) * angle) / 180UL;
  constexpr uint32_t MAX_DUTY = (1UL << SERVO_RESOLUTION_BITS) - 1UL;
  return (pulseUs * MAX_DUTY) / SERVO_PERIOD_US;
}

void writeServoAngle(uint8_t angle) {
  const uint32_t duty = angleToDuty(angle);
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(SERVO_PIN, duty);
#else
  ledcWrite(SERVO_LEDC_CHANNEL, duty);
#endif
}

void moveServoTo(uint8_t targetAngle) {
  if (targetAngle > 180) targetAngle = 180;
  Serial.printf("Move: %u -> %u\n",
                static_cast<unsigned>(currentAngle),
                static_cast<unsigned>(targetAngle));

  while (currentAngle != targetAngle) {
    if (currentAngle < targetAngle) {
      const uint8_t remaining = targetAngle - currentAngle;
      currentAngle += (remaining < ANGLE_STEP) ? remaining : ANGLE_STEP;
    } else {
      const uint8_t remaining = currentAngle - targetAngle;
      currentAngle -= (remaining < ANGLE_STEP) ? remaining : ANGLE_STEP;
    }
    writeServoAngle(currentAngle);
    delay(STEP_DELAY_MS);
  }
  Serial.printf("Reached: %u\n", static_cast<unsigned>(currentAngle));
}

bool initServo() {
  pinMode(USER_LED_PIN, OUTPUT);
  digitalWrite(USER_LED_PIN, HIGH);
  pinMode(SERVO_PIN, OUTPUT);
  digitalWrite(SERVO_PIN, LOW);

#if ESP_ARDUINO_VERSION_MAJOR >= 3
  const bool ok = ledcAttach(SERVO_PIN, SERVO_FREQ_HZ, SERVO_RESOLUTION_BITS);
#else
  ledcSetup(SERVO_LEDC_CHANNEL, SERVO_FREQ_HZ, SERVO_RESOLUTION_BITS);
  ledcAttachPin(SERVO_PIN, SERVO_LEDC_CHANNEL);
  const bool ok = true;
#endif
  writeServoAngle(SERVO_CLOSED_ANGLE);
  currentAngle = SERVO_CLOSED_ANGLE;
  return ok;
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
  if (packet.magic == PACKET_MAGIC && packet.version == PROTOCOL_VERSION) {
    if (packet.command == CMD_MOVE_180) {
      receivedSequence = packet.sequence;
      commandPending = true;
    } else if (packet.command == CMD_SERVO_RESET) {
      resetPending = true;
    }
  }
}

bool connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  const uint32_t startMs = millis();
  while (WiFi.status() != WL_CONNECTED &&
         static_cast<uint32_t>(millis() - startMs) < WIFI_CONNECT_TIMEOUT_MS) {
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

bool beginEspNow() {
  if (esp_now_init() != ESP_OK) return false;
  esp_now_register_recv_cb(onDataRecv);
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("XIAO ESP32C6 Servo Receiver - 0/180, 35 seconds");

  if (!initServo()) {
    Serial.println("FAIL: LEDC PWM init failed");
    for (;;) delay(1000);
  }

  connectWifi();

  if (!beginEspNow()) {
    Serial.println("FAIL: ESP-NOW init failed");
    for (;;) delay(1000);
  }

  Serial.printf("MAC: %s\n", WiFi.macAddress().c_str());
  Serial.println("PASS: receiver ready at 0 degrees.");
}

void handleSerialTestCommands() {
  while (Serial.available() > 0) {
    const char command = static_cast<char>(toupper(Serial.read()));
    if (command == 'O') {
      commandPending = true;
      Serial.println("Serial test: MOVE_180");
    } else if (command == 'R') {
      resetPending = true;
      Serial.println("Serial test: RESET");
    }
  }
}

void loop() {
  const uint32_t now = millis();
  handleSerialTestCommands();

  if (resetPending) {
    resetPending = false;
    commandPending = false;
    servoActive = false;
    moveServoTo(SERVO_CLOSED_ANGLE);
    digitalWrite(USER_LED_PIN, HIGH);
    Serial.println("RESET command: servo forced to 0 degrees.");
  }

  if (commandPending) {
    commandPending = false;

    if (!servoActive) {
      servoActive = true;
      digitalWrite(USER_LED_PIN, LOW);
      moveServoTo(SERVO_OPEN_ANGLE);
      activeUntilMs = millis() + SERVO_ACTIVE_MS;
      Serial.printf("Command received, sequence=%u. Hold 35 seconds.\n",
                    static_cast<unsigned>(receivedSequence));
    } else {
      Serial.println("Duplicate command ignored.");
    }
  }

  if (servoActive && static_cast<int32_t>(now - activeUntilMs) >= 0) {
    servoActive = false;
    moveServoTo(SERVO_CLOSED_ANGLE);
    digitalWrite(USER_LED_PIN, HIGH);
    Serial.println("35 seconds complete. Servo returned to 0 degrees.");
  }

  delay(10);
}
