# 設定參考（公開版）

本公開版不包含任何真實 Wi-Fi、API Token、Google Apps Script 部署網址或韌體二進位檔。

## 部署前需要自行設定

| 項目 | 應放置位置 | 公開版值 |
|---|---|---|
| Wi-Fi SSID | `01_ESP32S3_RFID_Sender`、`02_ESP32_WROOM_Timer_Server`、`03_XIAO_ESP32C6_Servo_Receiver` | `YOUR_WIFI_SSID` |
| Wi-Fi 密碼 | 同上 | `YOUR_WIFI_PASSWORD` |
| Apps Script Web App URL | `01_ESP32S3_RFID_Sender` | `YOUR_APPS_SCRIPT_WEB_APP_URL` |
| API Token | ESP32 發送端及 `04_GoogleAppsScript` | `CHANGE_ME_RANDOM_TOKEN` |
| AP 密碼 | `02_ESP32_WROOM_Timer_Server` | `CHANGE_ME_AP_PASSWORD` |

## 安全要求

1. 不要直接提交真實密碼或 Token。
2. 建議使用本機 `secrets.h`、環境變數或部署時注入。
3. 若曾把憑證上傳到任何公開位置，應立即撤銷並重新產生。
4. `05_Firmware_Binary` 未包含在公開版，因為二進位可能內嵌憑證；請從已設定的原始碼重新編譯。
