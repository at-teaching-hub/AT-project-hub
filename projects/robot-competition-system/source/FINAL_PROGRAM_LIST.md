# 最終程式碼清單

## 1. ESP32-S3 拍卡發送端

**檔案：** `01_ESP32S3_RFID_Sender/RFID_GoogleSheet_Sender.ino`  
**開發板：** Waveshare ESP32-S3 Zone／Zero；Arduino IDE 亦可選 `ESP32S3 Dev Module`  
**程式庫：** `MFRC522 by GithubCommunity`（Miguel Balboa 版本）  
**序列速度：** 115200 baud

功能：

- 讀取 RC522 卡片 UID。
- 由 Google Apps Script 讀取 `CARD` 工作表，建立 UID → Route 對照。
- 開機時載入一次，待機期間每 5 分鐘刷新。
- 只接受 Google Sheet 存在的卡；不接受未設定卡或 Route 為 `?`。
- 拍卡後立即經 ESP-NOW 把 Route 傳給 WROOM，令網頁立即顯示及開始計時。
- 等待 5 秒後，再經 ESP-NOW 廣播 `MOVE_180` 給 C6。
- 將接受／拒絕結果寫入 `result` 工作表。
- 收到 WROOM 的 RESET 廣播後返回 READY。

主要參數：

```cpp
CARD_DELAY_MS = 5000
SERVO_ACTIVE_MS = 35000
CARD_REFRESH_MS = 300000
```

RC522 接線：

| RC522 | ESP32-S3 |
|---|---|
| SDA／SS | D10／GPIO10 |
| SCK | D13／GPIO13 |
| MOSI | D11／GPIO11 |
| MISO | D12／GPIO12 |
| RST | D9／GPIO9 |
| 3.3V | 3V3 |
| GND | GND |
| IRQ | 不接 |

---

## 2. ESP32 WROOM 32 網頁計時及控制

**主要程式：** `02_ESP32_WROOM_Timer_Server/ESP32_WROOM_Timer_Server.ino`  
**網頁來源：** `web_page.h`（Arduino 實際編譯使用）  
**可編輯網頁：** `index.html`  
**開發板：** `ESP32 Dev Module`  
**FQBN：** `esp32:esp32:esp32`  
**上載速度：** 115200（本機 WROOM 實測必須用此速度）  
**序列速度：** 115200 baud

功能：

- 接收 S3 的 Route 事件，立即啟動計時。
- 顯示 Route、即時時間及最終時間；時間顯示至小數後 2 位。
- D4／D17 壓力感應器：任何穩定的電平變化均會停止計時，支援 active-high／active-low。
- GPIO18：實體停止按鈕，另一端接 GND。
- GPIO19：實體重設按鈕，另一端接 GND。
- 網頁「終止計時」及「重設系統」按鈕。
- 重設時經 ESP-NOW 廣播 RESET 給 S3 及 C6。
- 連上路由器後仍會開啟 `RobotTimer` AP，方便手機在現場查看網頁。

主要接腳：

| 功能 | WROOM GPIO |
|---|---|
| 壓力感應器 A | GPIO4 |
| 壓力感應器 B | GPIO17 |
| STOP 按鈕 | GPIO18 → GND |
| RESET 按鈕 | GPIO19 → GND |

**注意：** GPIO6–GPIO11 是 WROOM Flash 專用腳，不可接感應器或按鈕。

主要網址：

- `http://<WROOM路由器IP>/`
- `http://<WROOM路由器IP>/status`
- 本地 AP：`RobotTimer`／`YOUR_AP_PASSWORD`
- 本地 AP 網址：`http://192.168.4.1/`

---

## 3. Seeed XIAO ESP32C6 伺服接收端

**檔案：** `03_XIAO_ESP32C6_Servo_Receiver/ESP_NOW_C6_Servo_Receiver_35s.ino`  
**開發板：** Seeed XIAO ESP32C6  
**伺服訊號：** D9／GPIO20  
**序列速度：** 115200 baud

功能：

- 收到 ESP-NOW `MOVE_180` 後，伺服由 0° 平滑轉到 180°。
- 保持 180° 共 35 秒。
- 35 秒後自動返回 0°。
- 收到 RESET 時立即返回 0°。
- 同一輪重複指令會被忽略。

主要參數：

```cpp
SERVO_PIN = 20
SERVO_CLOSED_ANGLE = 0
SERVO_OPEN_ANGLE = 180
SERVO_ACTIVE_MS = 35000
```

---

## 4. Google Apps Script

**檔案：** `04_GoogleAppsScript/RobotCompetitionSheet.gs`

功能：

- `action=cards`：回傳 `UID|ROUTE` 清單給 ESP32-S3。
- `action=log`：把拍卡結果寫入 `result`。
- Token 必須與 ESP32-S3 內的 `API_TOKEN` 完全相同。
- 支援以下兩種 CARD 表排列：
  - 建議：A = ROUTE，B = CARD NUMBER。
  - 反向：A = CARD NUMBER，B = ROUTE；腳本會根據標題自動辨認。

目前卡片資料：

| Route | Card UID |
|---|---|
| A | E3:8C:E9:38 |
| B | DD:D5:DB:CD |
| C | 5D:6F:C3:CD |

---

## 5. WROOM 已編譯韌體

**檔案：** `05_Firmware_Binary/ESP32_WROOM_Timer_Server.ino.merged.bin`  
**用途：** 可直接以 esptool 寫入 ESP32 WROOM，位址 `0x0`。  
**建議：** 日後修改程式時仍應使用 Arduino IDE 重新編譯，不應修改二進位檔。

參考指令：

```powershell
esptool.exe --chip esp32 --port COM10 --baud 115200 \
  write-flash -z 0x0 ESP32_WROOM_Timer_Server.ino.merged.bin
```

COM 埠會因電腦及插入位置改變，執行前必須確認。

---

## ESP-NOW 封包

- 廣播 MAC：`FF:FF:FF:FF:FF:FF`
- Magic：`0x5A4F4E45`
- Protocol Version：1
- CardEventPacket：16 bytes，S3 → WROOM，內容包括 Route 及 sequence。
- CommandPacket：8 bytes，用於 `MOVE_180` 及 `SERVO_RESET`。
- 三塊板連接同一 Wi-Fi AP，ESP-NOW peer channel 使用目前 Wi-Fi channel。

---

## 版本

- Arduino IDE：2.3.8
- Arduino-ESP32 Core：3.3.12
- 測試日期：2026-11-18
- 已測試成功：拍卡、Route、計時、GPIO18 停止、GPIO19 重設、D4／D17 壓力停止、C6 伺服動作。
