/*
 * ESP32-C3 Super Mini 壓力感測器診斷測試
 *
 * 預設接線：
 *   感測器 VCC -> 3V3
 *   感測器 GND -> GND
 *   感測器 AO / OUT -> GPIO4（板上的 4；不是 USB D+）
 *
 * 若實際接在 GPIO3，將下面 PRESSURE_PIN 改成 3 後重新上傳。
 * 注意：不同 ESP32-C3 板子的 ADC 有效輸入範圍與線性度不同；
 * 本程式輸出原始 ADC 和校準後 mV，不直接把 ADC 當成 kgf/N 等物理單位。
 */

#ifndef PRESSURE_PIN
#define PRESSURE_PIN 4
#endif

constexpr uint32_t SERIAL_BAUD = 115200;
constexpr uint8_t  ADC_BITS = 12;
constexpr uint8_t  SAMPLES_PER_REPORT = 32;
constexpr uint32_t REPORT_INTERVAL_MS = 500;
constexpr uint32_t SAMPLE_SPACING_US = 500;

struct SensorReading {
  uint16_t rawAverage;
  uint16_t rawMinimum;
  uint16_t rawMaximum;
  uint16_t mvAverage;
  uint16_t mvMinimum;
  uint16_t mvMaximum;
};

uint32_t lastReportMs = 0;

SensorReading readSensor() {
  uint32_t rawSum = 0;
  uint32_t mvSum = 0;
  uint16_t rawMin = 4095;
  uint16_t rawMax = 0;
  uint16_t mvMin = 65535;
  uint16_t mvMax = 0;

  for (uint8_t i = 0; i < SAMPLES_PER_REPORT; ++i) {
    const uint16_t raw = analogRead(PRESSURE_PIN);
    const uint16_t mv = static_cast<uint16_t>(analogReadMilliVolts(PRESSURE_PIN));

    rawSum += raw;
    mvSum += mv;
    rawMin = min(rawMin, raw);
    rawMax = max(rawMax, raw);
    mvMin = min(mvMin, mv);
    mvMax = max(mvMax, mv);

    delayMicroseconds(SAMPLE_SPACING_US);
  }

  return {
    static_cast<uint16_t>((rawSum + SAMPLES_PER_REPORT / 2) / SAMPLES_PER_REPORT),
    rawMin,
    rawMax,
    static_cast<uint16_t>((mvSum + SAMPLES_PER_REPORT / 2) / SAMPLES_PER_REPORT),
    mvMin,
    mvMax
  };
}

const char* diagnose(const SensorReading& r) {
  const uint16_t rawRange = r.rawMaximum - r.rawMinimum;

  if (r.rawMaximum >= 4090 || r.rawAverage >= 4080) {
    return "ADC 接近滿刻度：可能過壓、接錯電源或超出可量測範圍";
  }
  if (r.rawAverage <= 15 && r.rawMaximum <= 25) {
    return "ADC 接近 0：可能接地、感測器未供電或訊號腳位錯誤";
  }
  if (rawRange >= 800) {
    return "讀值波動很大：可能浮接、GND 未共地、供電不穩或雜訊";
  }
  if (rawRange >= 200) {
    return "讀值波動偏大：請檢查接線與接觸品質";
  }
  return "ADC 讀值穩定，可開始施加/釋放壓力觀察變化";
}

void setup() {
  Serial.begin(SERIAL_BAUD);

  // 給原生 USB CDC 一點時間重新連線；最多等 3 秒，不讓開發板卡死。
  const uint32_t waitStart = millis();
  while (!Serial && (millis() - waitStart < 3000)) {
    delay(10);
  }

  analogReadResolution(ADC_BITS);
  analogSetPinAttenuation(PRESSURE_PIN, ADC_11db);

  delay(200);

  Serial.println();
  Serial.println("ESP32-C3 壓力感測器診斷測試已啟動");
  Serial.printf("序列埠: %lu baud\n", static_cast<unsigned long>(SERIAL_BAUD));
  Serial.printf("訊號腳位: GPIO%d\n", PRESSURE_PIN);
  Serial.printf("ADC: %u-bit, 11 dB attenuation, 每次回報 %u samples\n\n",
                ADC_BITS, SAMPLES_PER_REPORT);
  Serial.println("時間(ms) | ADC平均 | ADC最小 | ADC最大 | 範圍 | mV平均 | 狀態");
  Serial.println("---------------------------------------------------------------");

  lastReportMs = millis();
}

void loop() {
  const uint32_t now = millis();
  if (now - lastReportMs < REPORT_INTERVAL_MS) {
    delay(5);
    return;
  }
  lastReportMs = now;

  const SensorReading r = readSensor();

  Serial.printf("%8lu | %7u | %7u | %7u | %4u | %6u | %s\n",
                static_cast<unsigned long>(now),
                r.rawAverage,
                r.rawMinimum,
                r.rawMaximum,
                static_cast<unsigned int>(r.rawMaximum - r.rawMinimum),
                r.mvAverage,
                diagnose(r));
}