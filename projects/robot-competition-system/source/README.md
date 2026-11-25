# 30周年校慶杯機械人奪寳奇兵桃戰賽 — 最終系統包

整理日期：2026-11-18  
狀態：已完成硬件實測，拍卡、Route、計時、GPIO18 停止、GPIO19 重設、D4／D17 壓力停止均已測試成功。

## 文件閱讀順序

1. `FINAL_PROGRAM_LIST.md` — 最終程式碼清單、版本及用途。
2. `SYSTEM_DOCUMENTATION.md` — 系統架構、接線、設定、操作及上載方法。
3. `TROUBLESHOOTING_AND_PRECAUTIONS.md` — 故障排查、注意事項及比賽前檢查表。
4. `CONFIG_REFERENCE.md` — 目前 Wi-Fi、Token、Sheet 及主要參數。
5. `MULTI_SYSTEM_DEPLOYMENT.md` — 同一場地同時運行多套系統的隔離方法。

## 資料夾內容

```text
RobotCompetition_System_Final
├─ 01_ESP32S3_RFID_Sender
│  └─ RFID_GoogleSheet_Sender.ino
├─ 02_ESP32_WROOM_Timer_Server
│  ├─ ESP32_WROOM_Timer_Server.ino
│  ├─ web_page.h
│  ├─ index.html
│  └─ sketch.yaml
├─ 03_XIAO_ESP32C6_Servo_Receiver
│  └─ ESP_NOW_C6_Servo_Receiver_35s.ino
├─ 04_GoogleAppsScript
│  └─ RobotCompetitionSheet.gs
├─ 05_Firmware_Binary
│  └─ ESP32_WROOM_Timer_Server.ino.merged.bin
├─ FINAL_PROGRAM_LIST.md
├─ SYSTEM_DOCUMENTATION.md
├─ TROUBLESHOOTING_AND_PRECAUTIONS.md
├─ CONFIG_REFERENCE.md
├─ MULTI_SYSTEM_DEPLOYMENT.md
└─ CHECKSUMS.sha256
```

## 三個控制器

- **ESP32-S3 + RC522**：讀卡、由 Google Sheet 查 Route、經 ESP-NOW 通知 WROOM，5 秒後通知 C6 開伺服。
- **ESP32 WROOM 32**：網頁計時器、Route 顯示、D4／D17 壓力停止、GPIO18 停止、GPIO19 重設。
- **Seeed XIAO ESP32C6**：D9／GPIO20 控制伺服，0° → 180°，保持 35 秒，返回 0°。

## 重要提醒

- 三塊板必須連接同一個 **2.4 GHz Wi-Fi**，ESP-NOW 頻道才會一致。
- 手機看不到路由器網頁時，連接 WROOM 的 `RobotTimer` AP（密碼請自行設定），再開 `http://192.168.4.1/`。
- 此 AP 只用於本地網頁；S3 仍須連接有互聯網的 2.4 GHz 路由器，才能讀取 Google Sheet。
- 伺服馬達必須使用獨立、足夠電流的 5V 電源，並與 C6 共地。
- 本資料夾含 API Token 及 Wi-Fi 密碼，請勿公開上載到公共網上。
