// 定義壓力感應器連接的腳位
const int PRESSURE_PIN = 3; 

void setup() {
  // 初始化序列埠通訊，ESP32-C3 建議使用 115200 鮑率
  Serial.begin(115200);
  
  // 延遲 2 秒，確保 ESP32-C3 的內建 USB CDC 序列埠有足夠時間連線
  delay(2000); 
  Serial.println("ESP32-C3 壓力感應器測試系統已啟動...");
}

void loop() {
  // 讀取 GPIO4 的類比數值
  // ESP32-C3 的 ADC 解析度預設為 12-bit，數值範圍是 0 到 4095
  int pressureValue = analogRead(PRESSURE_PIN);
  
  // 輸出數值到序列埠監控視窗
  Serial.print("當前壓力數值: ");
  Serial.println(pressureValue);
  
  // 延遲 500 毫秒 (0.5秒) 後再次讀取，方便肉眼觀察數值變化
  delay(500);
}