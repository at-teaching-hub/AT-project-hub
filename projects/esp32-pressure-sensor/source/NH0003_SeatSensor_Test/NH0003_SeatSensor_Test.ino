/*
 * NH0003 座椅壓力感測器 + LM393 壓力信號轉換模組
 *
 * 建議接線（數位模式）：
 *   NH0003 兩條線 -> 模組的壓力感測器輸入端（文件標示不分正負）
 *   模組 VCC      -> ESP32-C3 3V3
 *   模組 GND      -> ESP32-C3 GND
 *   模組 DO       -> GPIO4
 *   模組 AO       -> 本模式不接
 *
 * 文件定義：未受壓/未達門檻時 DO 為 HIGH；受壓超過門檻時 DO 為 LOW。
 * 可用模組上的靈敏度電位器調整觸發門檻。
 *
 * 重要：
 * 1. NH0003 是薄膜觸點感測器，主要用於「有/無壓力」或座椅佔用判斷，
 *    不是可線性量測 kgf、kg 或 N 的稱重感測器。
 * 2. 若使用 AO，模組請用 3.3 V 供電，且 AO 不得超過 ESP32-C3 的 ADC 範圍。
 *    文件標示模組輸出可到 VCC；用 5 V 供電時不可把 AO/DO 直接接 ESP32-C3。
 * 3. AO 模式輸出的是未經壓力校正的類比訊號，不代表 kgf/kg/N。
 */

#define USE_DIGITAL_DO 1   // 1 = 使用 DO（推薦）；0 = 使用 AO 做類比診斷
#define SENSOR_PIN 4       // Super Mini 板上標示 4 = GPIO4

constexpr uint32_t SERIAL_BAUD = 115200;
constexpr bool DO_ACTIVE_LEVEL = LOW;
constexpr uint32_t DEBOUNCE_MS = 30;
constexpr uint32_t STATUS_INTERVAL_MS = 2000;
constexpr uint8_t  ANALOG_SAMPLES = 32;

uint32_t lastStatusMs = 0;
uint32_t lastChangeMs = 0;
bool lastRawState = false;
bool stableState = false;

#if USE_DIGITAL_DO
void setupSensor() {
  // 模組通常已有上拉；內部上拉可避免 DO 未接時浮動。
  pinMode(SENSOR_PIN, INPUT_PULLUP);
}

void testSensor() {
  const bool rawState = digitalRead(SENSOR_PIN) == DO_ACTIVE_LEVEL;
  const uint32_t now = millis();

  if (rawState != lastRawState) {
    lastRawState = rawState;
    lastChangeMs = now;
  }

  if (rawState != stableState && (now - lastChangeMs) >= DEBOUNCE_MS) {
    stableState = rawState;
    Serial.printf("[狀態變化] DO=%s，%s\n",
                  digitalRead(SENSOR_PIN) == HIGH ? "HIGH" : "LOW",
                  stableState ? "偵測到壓力／座椅有人" : "未偵測到壓力／座椅無人");
  }

  if (now - lastStatusMs >= STATUS_INTERVAL_MS) {
    lastStatusMs = now;
    Serial.printf("[持續狀態] DO=%s，%s\n",
                  digitalRead(SENSOR_PIN) == HIGH ? "HIGH" : "LOW",
                  stableState ? "受壓" : "未受壓");
  }
}
#else
void setupSensor() {
  analogReadResolution(12);
  analogSetPinAttenuation(SENSOR_PIN, ADC_11db);
}

void testSensor() {
  uint32_t rawSum = 0;
  uint32_t mvSum = 0;
  uint16_t rawMin = 4095;
  uint16_t rawMax = 0;

  for (uint8_t i = 0; i < ANALOG_SAMPLES; ++i) {
    const uint16_t raw = analogRead(SENSOR_PIN);
    const uint16_t mv = static_cast<uint16_t>(analogReadMilliVolts(SENSOR_PIN));
    rawSum += raw;
    mvSum += mv;
    rawMin = min(rawMin, raw);
    rawMax = max(rawMax, raw);
    delayMicroseconds(500);
  }

  const uint16_t rawAvg = (rawSum + ANALOG_SAMPLES / 2) / ANALOG_SAMPLES;
  const uint16_t mvAvg = (mvSum + ANALOG_SAMPLES / 2) / ANALOG_SAMPLES;
  const uint32_t now = millis();

  if (now - lastStatusMs >= 500) {
    lastStatusMs = now;
    Serial.printf("[AO] raw=%u min=%u max=%u range=%u mV=%u（未校正為壓力單位）\n",
                  rawAvg, rawMin, rawMax,
                  static_cast<unsigned int>(rawMax - rawMin), mvAvg);
  }
}
#endif

void setup() {
  Serial.begin(SERIAL_BAUD);

  const uint32_t waitStart = millis();
  while (!Serial && (millis() - waitStart < 3000)) {
    delay(10);
  }

  Serial.println();
  Serial.println("NH0003 座椅壓力感測器測試");
  Serial.printf("模式：%s，腳位：GPIO%d\n", USE_DIGITAL_DO ? "DO 數位" : "AO 類比", SENSOR_PIN);
  Serial.println(USE_DIGITAL_DO
    ? "提示：DO 未受壓 HIGH、受壓 LOW；必要時調整模組上的靈敏度電位器。"
    : "提示：AO 僅供診斷，不能直接視為 kgf/kg/N。");

  setupSensor();
  lastStatusMs = millis();
  lastChangeMs = millis();
  lastRawState = digitalRead(SENSOR_PIN) == DO_ACTIVE_LEVEL;
  stableState = lastRawState;
}

void loop() {
  testSensor();
#if USE_DIGITAL_DO
  delay(5);
#else
  delay(5);
#endif
}