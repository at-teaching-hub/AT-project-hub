# 故障排查、注意事項及比賽前檢查表

## 1. 快速判斷流程

```text
拍卡後沒有 Route
  → 看 S3 序列：Card UID 是否讀到？
  → 看 Google Sheet：CARD 名稱、欄位、Token、Web App /exec URL？

有 Route 但沒有計時
  → WROOM /status 是否 running？
  → S3 和 WROOM 是否同一 2.4GHz Wi-Fi channel？
  → 先用 WROOM 序列命令 T 測試計時。

計時中按壓感應器不停止
  → /status 的 d4、d17、pressureState、pressureBaseline 是否改變？
  → 感應器是否在拍卡前已經按住？
  → 感應器輸出是否 3.3V 安全電平？

伺服不轉
  → C6 是否收到 ESP-NOW？
  → C6 D9／GPIO20 是否接對？
  → 伺服是否有獨立 5V 電源及共地？

網頁看不到
  → 手機是否連 RobotTimer？
  → 是否開 http://192.168.4.1/？
  → WROOM 是否正常供電及啟動？
```

## 2. 常見問題

### 2.1 RC522 完全讀不到卡

檢查：

- RC522 是否接 3.3V，而不是 5V。
- SDA／SS 是否接 S3 的 D10／GPIO10；它不是 I2C SDA。
- SCK 是否 D13、MOSI 是否 D11、MISO 是否 D12。
- RST 是否 D9；GND 是否共地。
- S3 序列監視器是否顯示合理 RC522 版本寄存器；`0x00` 或 `0xFF` 通常代表接線／電源問題。
- 卡片是否靠近天線中心。
- 排線是否過長或接觸不良。

### 2.2 拍卡後 Route 顯示「?」或空白

- 確認 S3 的 `SHEETS_WEB_APP_URL` 是最後部署的 `/exec` URL。
- 確認 Apps Script 已建立「新版本」部署，而不是只儲存程式碼。
- 確認執行身分為「我」，存取權為「任何人」。
- 確認 `API_TOKEN` 與 `RobotCompetitionSheet.gs` 的 `CONFIG.API_TOKEN` 完全相同。
- 確認 Sheet 名稱是 `robot competition result`，分頁是 `CARD` 和 `result`。
- CARD 建議 A=ROUTE、B=CARD NUMBER；若反轉，標題必須清楚寫出 CARD NUMBER／ROUTE。
- S3 開機或重新啟動後，會立即重新讀取 Sheet。

### 2.3 有 Route 但計時沒有開始

- 檢查 WROOM 與 S3 是否連接同一個 2.4GHz AP。
- 若有一塊板 Wi-Fi 失敗，可能落在 fallback channel 1，channel 不一致就不會收到 ESP-NOW。
- 用 WROOM Serial Monitor 輸入 `T`；若 `T` 能開始計時，問題通常在 S3→WROOM 的 ESP-NOW／Wi-Fi channel。
- 確認 WROOM 的 IP／AP 正常啟動，序列監視器應顯示 `softAP result=OK`。
- 三塊板都應使用同一版本協定：Magic `0x5A4F4E45`、Protocol Version 1。

### 2.4 壓力感應器停不了計時

本版本已改為偵測 **任何穩定電平變化**，支援 active-high 及 active-low。

先開啟：

```text
http://192.168.4.1/status
```

觀察：

```json
{
  "state": "running",
  "d4": 1,
  "d17": 0,
  "pressureState": 1,
  "pressureBaseline": 0
}
```

處理：

- 拍卡前不要按住壓力板；程式會把當時狀態作為 baseline。
- 如果 baseline 與按下時完全相同，先放開感應器，再重新按下。
- 確認訊號線接 D4 或 D17，而不是其他 GPIO。
- 確認感應器 VCC／GND 正常，模組指示燈有反應。
- 若模組輸出 5V，必須加電平轉換或分壓，不可直接輸入 ESP32。
- 若是模擬 FSR，將 `PRESSURE_ANALOG_MODE` 設為 `true`，重新設定 threshold。
- 單獨測試時可看序列訊息：

```text
STOP triggered by pressure change: D4=... D17=... baseline=... current=...
```

### 2.5 GPIO18 停止或 GPIO19 重設沒有反應

- 按鈕一端接 GPIO18／GPIO19，另一端接 GND。
- 程式使用 `INPUT_PULLUP`，按下時應由 HIGH 變 LOW。
- 不要接 3.3V 到按鈕另一端。
- 確認沒有使用 GPIO6–GPIO11。
- 用萬用表或序列監視器確認按下時 GPIO 狀態改變。

### 2.6 伺服馬達不轉

- 確認 C6 的 D9／GPIO20 接伺服 Signal。
- 確認伺服 V+ 使用獨立 5V，且 GND 與 C6 GND 共地。
- 確認 C6 沒有在啟動時顯示 LEDC init failed。
- 在 C6 Serial Monitor 輸入 `O` 測試 180°。
- 在 C6 Serial Monitor 輸入 `R` 測試回 0°。
- 確認 S3 在拍卡後 5 秒顯示 `ESP-NOW command queued`，而不是 send failed。
- 確認三塊板 Wi-Fi channel 相同。

### 2.7 伺服抖動、發熱或 C6 重啟

- 幾乎一定是馬達電流不足、沒有共地或電源電壓下跌。
- 使用獨立 5V／足夠電流電源，不要由 C6 供電。
- 在伺服電源兩端加 470–1000 µF 電容。
- 先拆下舵臂或負載測試，避免卡住堵轉。
- 如使用 MG996R 等高電流伺服，電源必須按峰值電流預留。

### 2.8 網頁打不開

- 手機連線 SSID：`RobotTimer`；密碼：`YOUR_AP_PASSWORD`。
- 瀏覽器開 `http://192.168.4.1/`。
- 若使用路由器模式，IP 可能改變；以 WROOM Serial Monitor 顯示為準，不要固定使用舊 IP。
- 確認 WROOM 有電、USB 線是數據線而非純充電線。
- 若手機仍連著其他 Wi-Fi，先切換到 RobotTimer。
- 本地 AP 只提供網頁；S3 的 Google Sheet 仍需互聯網路由器。

### 2.9 Apps Script 寫入 result 失敗

- 重新部署 Apps Script 新版本。
- 確認存取權為「任何人」。
- 確認部署 URL 結尾是 `/exec`。
- 確認 Token 沒有多餘空格。
- 檢查 Google Sheet 的 result 分頁是否被重新命名或刪除。
- 若 Google 帳戶權限或組織政策改變，重新檢查部署權限。

### 2.10 Arduino 上載失敗

- WROOM 已實測 Upload Speed 用 115200；不要先用 921600。
- 確認選擇正確的 COM Port，不要誤選其他 ESP32。
- 關閉 Serial Monitor 或其他佔用 COM Port 的程式。
- 使用可傳數據的 USB 線。
- 若顯示 flash chip connection 失敗，先重插 USB、換線或按住 BOOT 再上載。
- WROOM 的 COM Port 可能因插拔改變；更新 `sketch.yaml` 或 IDE Port 選擇。

### 2.11 拍卡後重複觸發

- S3 在成功發送後會進入 35 秒冷卻。
- C6 會忽略同一輪重複 MOVE_180。
- 若要開始下一輪，必須按 GPIO19／網頁重設，或等待 S3／C6 冷卻完成。
- 確認沒有兩張相同 UID 的卡同時被掃到。

## 3. 重要注意事項

### 電氣安全

- RC522 只可接 3.3V。
- ESP32 GPIO 不可直接承受 5V。
- 伺服馬達不可由 GPIO 供電。
- 伺服必須使用獨立、電流足夠的 5V 電源。
- 所有控制板、感應器及伺服電源必須共地。
- 拔插任何接線前先切斷電源。
- 不要使用 WROOM GPIO6–GPIO11；它們是 Flash 腳。

### 資料及版本

- 本資料夾含 Wi-Fi 密碼及 API Token，請勿公開分享。
- 修改 Apps Script 後，必須部署新版本；只按儲存不會更新 Web App。
- 修改 `index.html` 後，記得同步 `web_page.h`。
- 三塊板的 ESP-NOW 協定版本、Magic、Channel 必須一致。
- 保留 `CHECKSUMS.sha256`，以便日後核對檔案是否被意外修改。

## 4. 比賽前檢查表

- [ ] RC522 3.3V、GND、SPI 五條線穩固。
- [ ] S3 能讀到三張卡的 UID。
- [ ] Google Sheet CARD 表有正確 Route／Card number。
- [ ] Apps Script Token 正確，Web App 部署可用。
- [ ] S3、WROOM、C6 都連同一個 2.4GHz Wi-Fi。
- [ ] WROOM 顯示 `softAP result=OK`。
- [ ] 手機可連接 RobotTimer 並打開 `http://192.168.4.1/`。
- [ ] 拍卡後 Route 正確，計時由 0:00.00 開始。
- [ ] D4 壓力感應能停止，D17 壓力感應能停止。
- [ ] GPIO18 停止按鈕正常。
- [ ] GPIO19 重設按鈕正常。
- [ ] 網頁「終止計時」及「重設系統」正常。
- [ ] 5 秒後伺服轉 180°，35 秒後回 0°。
- [ ] 伺服電源沒有明顯電壓下跌，C6 沒有重啟。
- [ ] result 表有寫入測試結果。
- [ ] 已備份 Google Sheet、Apps Script 及本資料夾。

## 5. 故障時保留的資料

如日後需要再排查，請保留：

1. WROOM 的 `/status` JSON。
2. 三塊板的 Serial Monitor 輸出（115200 baud）。
3. 拍卡時的 Card UID。
4. 異常時的 Route、停止原因及最終時間。
5. 哪一個壓力腳（D4／D17）、按鈕或網頁操作觸發／未觸發。
6. 目前 Arduino IDE Board、COM Port、Upload Speed 及 ESP32 Core 版本。
