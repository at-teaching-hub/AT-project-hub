# 系統說明書

## 1. 系統目的

本系統供「十八鄉鄉事委員會公益社中學30周年校慶杯機械人奪寳奇兵桃戰賽」使用。參賽者拍卡後，系統顯示卡所代表的路線字母並開始計時；壓力感應器或停止按鈕觸發時停止計時。拍卡 5 秒後，另一塊控制器會驅動伺服馬達，保持 35 秒後返回原位。

## 2. 系統架構

```text
┌──────────────────────────────┐
│ ESP32-S3 + RC522             │
│ 讀卡、Google Sheet 查 Route  │
└──────────────┬───────────────┘
               │ ESP-NOW：Route 事件（即時）
               ▼
┌──────────────────────────────┐
│ ESP32 WROOM 32               │
│ 顯示 Route、計時、停止、重設 │
└──────────────┬───────────────┘
               │ GPIO4／17、GPIO18、GPIO19
               ▼
        壓力感應器及按鈕

ESP32-S3 ── 等待 5 秒 ── ESP-NOW MOVE_180 ──► XIAO ESP32C6
                                             D9／GPIO20 → 伺服
                                             0° → 180°，保持 35 秒 → 0°
```

### 三個控制器

1. **ESP32-S3**：RC522 讀卡、Google Apps Script 查詢、ESP-NOW 發送。
2. **ESP32 WROOM 32**：Web Server、計時狀態、壓力／停止／重設輸入。
3. **Seeed XIAO ESP32C6**：伺服馬達 PWM 輸出及 35 秒保持計時。

## 3. 接線

### 3.1 ESP32-S3 與 RC522

| RC522 | ESP32-S3 |
|---|---|
| SDA／SS／CS | D10／GPIO10 |
| SCK | D13／GPIO13 |
| MOSI | D11／GPIO11 |
| MISO | D12／GPIO12 |
| RST | D9／GPIO9 |
| 3.3V | 3V3 |
| GND | GND |
| IRQ | 不接 |

- RC522 **只可接 3.3V**。
- RC522 的 SDA 是 SPI Chip Select，不是 I2C SDA。
- 若板子絲印不同，必須確認 D10、D13、D11、D12、D9 對應的 GPIO 編號。

### 3.2 ESP32 WROOM 32

| 功能 | GPIO | 接法 |
|---|---|---|
| 壓力感應器 A | GPIO4 | 感應器訊號；VCC／GND 按模組規格 |
| 壓力感應器 B | GPIO17 | 感應器訊號；與 GPIO4 任一觸發都會停止 |
| STOP 按鈕 | GPIO18 | 一端 GPIO18，另一端 GND |
| RESET 按鈕 | GPIO19 | 一端 GPIO19，另一端 GND |

數位模式使用 `INPUT_PULLUP`，並偵測任何穩定電平變化，因此 active-high 及 active-low 壓力板均可使用。

**壓力觸發注意：** 計時開始時會記錄 D4／D17 當時的基準。若在拍卡前已按住壓力板，該次不會因「持續按住」而停止；必須在計時開始後改變電平，或先放開再重新按下。

### 3.3 Seeed XIAO ESP32C6 與伺服馬達

| 伺服 | XIAO ESP32C6 |
|---|---|
| Signal／PWM | D9／GPIO20 |
| V+ | 獨立 5V 電源正極 |
| GND | 獨立 5V 電源負極 |
| XIAO GND | 必須與伺服 5V 電源地線共地 |

建議在伺服 5V 電源兩端加 470–1000 µF 電解電容。不要用 XIAO 的 3.3V 腳直接供應伺服馬達。

## 4. Google Sheet 設定

### 4.1 工作表

Google Sheet 名稱：

```text
robot competition result
```

工作表名稱：

```text
CARD
result
```

建議 CARD 格式：

| 儲存格 | 內容 |
|---|---|
| A1 | ROUTE |
| B1 | CARD NUMBER |
| A2:A | Route，例如 A、B、C |
| B2:B | 卡號 UID，例如 E3:8C:E9:38 |

目前實測卡號：

| Route | Card UID |
|---|---|
| A | E3:8C:E9:38 |
| B | DD:D5:DB:CD |
| C | 5D:6F:C3:CD |

Apps Script 也支援反向排列（A = CARD NUMBER、B = ROUTE），會按標題自動判斷。

### 4.2 Apps Script 部署

1. Google Sheet → 擴充功能 → Apps Script。
2. 以 `04_GoogleAppsScript/RobotCompetitionSheet.gs` 取代 Code.gs。
3. 確認 `CONFIG.API_TOKEN` 與 S3 程式中的 `API_TOKEN` 相同。
4. 部署 → 管理部署作業 → 編輯 → 新版本。
5. 執行身分選「我」；存取權選「任何人」。
6. 部署後使用結尾為 `/exec` 的 Web App URL。
7. 如建立新部署而 URL 改變，必須同步更新 S3 的 `SHEETS_WEB_APP_URL`。

### 4.3 result 工作表

腳本會自動建立或在現有 result 表追加以下欄位：

```text
TIMESTAMP | CARD NUMBER | RESULT | NOTE
```

## 5. Wi-Fi 及 ESP-NOW

三塊板正常運作時必須連接同一個 **2.4 GHz Wi-Fi AP**：

```text
SSID：YOUR_WIFI_SSID
Password：YOUR_WIFI_PASSWORD
```

重要：

- 5 GHz 專用 Wi-Fi 不適用。
- 三塊板必須在同一個 ESP-NOW Wi-Fi channel。程式以 AP 目前 channel 作為 ESP-NOW channel。
- 若其中一塊板 Wi-Fi 失敗，會使用 fallback channel 1；其他板仍連接路由器時，未必能互相通訊。
- WROOM 會另外開啟：
  ```text
  SSID：YOUR_WIFI_SSID
  Password：YOUR_WIFI_PASSWORD
  URL：http://192.168.4.1/
  ```
- 這個本地 AP 只方便手機查看網頁。S3 仍需要連接有互聯網的 2.4 GHz 路由器，才能讀取 Google Sheet。
- 不要硬編碼舊的路由器 IP（例如 192.168.x.x）；IP 可能因 DHCP 改變。請以 WROOM 序列監視器顯示的 IP 為準。

## 6. 正常操作流程

1. S3 開機，連接 Wi-Fi，從 Google Sheet 載入 UID → Route。
2. 拍卡。
3. S3 確認卡號存在，立即經 ESP-NOW 傳送 Route 給 WROOM。
4. WROOM 顯示 Route，計時器由 0:00.00 開始。
5. S3 等待 5 秒後，以 ESP-NOW 傳送 MOVE_180 給 C6。
6. C6 把伺服由 0° 轉到 180°，保持 35 秒，再返回 0°。
7. 以下任何一個事件會停止計時：
   - D4 壓力感應器出現穩定電平變化。
   - D17 壓力感應器出現穩定電平變化。
   - GPIO18 STOP 按鈕接地。
   - 網頁按「終止計時」。
8. 按 GPIO19 或網頁「重設系統」：
   - WROOM 回到 waiting。
   - 經 ESP-NOW 廣播 RESET。
   - S3 回復 READY。
   - C6 立即回到 0°。
9. 系統等待下一次拍卡。

## 7. 網頁計時器

網址：

- 連接 WROOM 本地 AP：`http://192.168.4.1/`
- 路由器模式：`http://<WROOM序列埠顯示的IP>/`
- 狀態 API：`http://<IP>/status`
- 停止 API：POST `/stop`
- 重設 API：POST `/reset`

頁面功能：

- Route／路線大字顯示。
- 計時由 0:00.00 開始，顯示至小數後兩位。
- 終止計時按鈕。
- 重設系統按鈕。
- 拍卡前顯示「等待AI辦認路線」。

## 8. 壓力感應器設定

目前設定：

```cpp
constexpr bool USE_PRESSURE_D4 = true;
constexpr bool USE_PRESSURE_D17 = true;
constexpr bool PRESSURE_ANALOG_MODE = false;
constexpr uint32_t PRESSURE_DEBOUNCE_MS = 30;
```

目前是「任何穩定電平變化」停止，不需要指定 HIGH 或 LOW 作觸發；這可兼容常見 active-high 及 active-low 數位壓力板。

如日後改成類比 FSR：

```cpp
constexpr bool PRESSURE_ANALOG_MODE = true;
constexpr bool PRESSURE_TRIGGER_HIGH = true;
constexpr int PRESSURE_THRESHOLD = 1500;
```

請先用序列監視器或 `/status` 確認實際 ADC 值，再調整門檻。

## 9. Arduino IDE 上載設定

### S3

- Board：`ESP32S3 Dev Module` 或 Waveshare 專用板卡。
- Serial Monitor：115200。
- 安裝 MFRC522 程式庫。
- 若 USB CDC 沒有 Log，將 USB CDC On Boot 設為 Enabled。
- 上載不穩時，Upload Speed 改為 115200。

### WROOM

- Board：`ESP32 Dev Module`。
- FQBN：`esp32:esp32:esp32`。
- Upload Speed：115200。
- Serial Monitor：115200。
- 本機 `sketch.yaml` 記錄 `default_port: COM10`；其他電腦可能不同，需重新選 Port。

### C6

- Board：Seeed XIAO ESP32C6。
- Servo Signal：D9／GPIO20。
- Serial Monitor：115200。
- Upload Speed 不穩時用 115200。
- 伺服使用外部 5V 並共地。

## 10. 序列測試指令

### WROOM

在 115200 Serial Monitor 輸入：

```text
T = 模擬拍卡，啟動 Route T 及計時
S = 停止計時
R = 重設系統，並廣播 RESET
O = 測試 MOVE_180
```

### C6

```text
O = 測試伺服 180°／35 秒
R = 強制返回 0°
```

## 11. 備份及修改原則

- CARD 工作表是路線資料的唯一來源；修改後 S3 最長 5 分鐘刷新，重新開機可立即刷新。
- 修改 Apps Script 後必須建立新版本部署；只儲存 Code.gs 不會更新已部署 Web App。
- 修改 `index.html` 後，Arduino 實際使用 `web_page.h`；必須確保兩者內容一致，否則網頁修改不會進入 Firmware。
- 修改 WROOM 後必須重新編譯及上載。
- 修改任何 ESP-NOW 參數（Magic、Protocol Version、Channel、封包格式）時，三塊板必須同步更新。
- 保留此資料夾及 CHECKSUMS 作日後回復用途。

## 12. 安全及硬件注意

- RC522 只接 3.3V，不要接 5V。
- ESP32 GPIO 不是 5V 容忍；如壓力模組輸出 5V，必須加電平轉換或分壓。
- 伺服馬達不可由 GPIO 供電。
- 伺服馬達必須使用獨立、額定電流足夠的 5V 電源。
- 所有控制板與伺服電源必須共地。
- 不要使用 WROOM 的 GPIO6–GPIO11，它們連接 Flash。
- 拔插接線前先斷電。
- 比賽前先備份 Google Sheet 及 Apps Script。
