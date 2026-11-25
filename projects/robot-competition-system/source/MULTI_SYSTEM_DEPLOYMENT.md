# 同一場地同時運行多套系統

## 1. 結論

目前版本只適合單套系統。同一室內同時運行兩套或以上時，**不可只靠不同電源或不同 Wi-Fi 名稱隔離**。

最簡單而有效的方案是：

1. 每套系統加入固定的 `SYSTEM_ID`。
2. 所有 ESP-NOW 封包帶上 `SYSTEM_ID`，接收端只處理相同 ID 的封包。
3. 每套 WROOM 使用不同 AP 名稱，例如 `RobotTimer-01`、`RobotTimer-02`。
4. Google Sheet 的 result 加入系統編號，或每套系統使用獨立 result 分頁。

這樣即使兩套系統在同一個 Wi-Fi AP、同一個 ESP-NOW channel、同一個房間，也不會互相啟動計時、互相重設或控制錯伺服。

## 2. 現時可能發生的問題

### 2.1 拍一張卡，多個計時器同時開始

目前的 S3 使用廣播 MAC：

```text
FF:FF:FF:FF:FF:FF
```

所有同一 Wi-Fi channel 的 WROOM 都會收到 Route 事件，可能同時顯示 Route 並開始計時。

### 2.2 一套按重設，另一套也被重設

WROOM 的 RESET 亦是廣播。所有 S3 及 C6 都可能收到，造成另一套系統的拍卡狀態、計時及伺服一併重設。

### 2.3 伺服馬達被另一套系統控制

S3 的 MOVE_180 是廣播。所有 C6 都可能收到並轉動伺服，造成 A 系統拍卡、B 系統閘門同時動作。

### 2.4 手機接錯 AP

目前多個 WROOM 都建立同名 AP：

```text
RobotTimer
12345678
192.168.4.1
```

手機會連接最強訊號的其中一個 AP，但現場人員無法知道連到哪一套系統。兩套系統的網址同為 192.168.4.1，會造成混亂。

### 2.5 Google Sheet 結果混合

多套 S3 共用同一 `result` 表時，紀錄會混在一起，無法分辨哪一筆屬於哪一套系統。若各系統使用不同卡或 Route，共用 CARD 表亦會出錯。

### 2.6 Channel 相同時干擾最大

ESP-NOW 會跟隨 Wi-Fi channel：

- 同一個路由器／AP：所有系統通常在同一 channel，互相收到的機會最高。
- 不同路由器但 channel 相同：仍然會互相收到。
- 只有不同 channel 才可能在無線層避開，但 channel 不一定可自由控制。

因此 **channel 分離不可作為唯一方案**。

## 3. 最簡單有效方案：SYSTEM_ID 過濾

### 3.1 建議命名

| 系統 | SYSTEM_ID | AP SSID | mDNS | 結果標記 |
|---|---:|---|---|---|
| 第一套 | 1 | RobotTimer-01 | robot-timer-01 | SYS01 |
| 第二套 | 2 | RobotTimer-02 | robot-timer-02 | SYS02 |
| 第三套 | 3 | RobotTimer-03 | robot-timer-03 | SYS03 |

### 3.2 三塊板都要有相同 SYSTEM_ID

S3、WROOM、C6 都要設定：

```cpp
constexpr uint8_t SYSTEM_ID = 1;  // 第二套改成 2
```

更換整套系統時，三塊板的 SYSTEM_ID 必須一起改。

### 3.3 封包加入 systemId

概念示例：

```cpp
struct __attribute__((packed)) CommandPacket {
  uint32_t magic;
  uint8_t version;
  uint8_t systemId;
  uint8_t command;
  uint8_t reserved;
  uint16_t sequence;
};

struct __attribute__((packed)) CardEventPacket {
  uint32_t magic;
  uint8_t version;
  uint8_t systemId;
  uint8_t eventType;
  uint8_t reserved;
  uint16_t sequence;
  char route[8];
};
```

發送前填寫：

```cpp
packet.systemId = SYSTEM_ID;
```

所有 `onDataRecv()` 必須先檢查：

```cpp
if (packet.systemId != SYSTEM_ID) return;
```

最少要修改：

- S3：CardEvent 及 MOVE_180 加入 systemId；收到 RESET 時檢查。
- WROOM：收到 Route 時檢查；發送 RESET 時加入。
- C6：收到 MOVE_180／RESET 時檢查。

### 3.4 為什麼不只用 MAC 單播？

固定 MAC 單播更嚴密，但需要記錄 WROOM 及 C6 的 MAC，並在 S3、WROOM 中設定 peer；換板後要重新配置。對小型比賽，`SYSTEM_ID` 過濾已經足夠，維護亦最少。

## 4. AP SSID 分離

WROOM 建立 AP 時加入系統編號：

```cpp
char apSsid[24];
snprintf(apSsid, sizeof(apSsid), "RobotTimer-%02u", SYSTEM_ID);
WiFi.softAP(apSsid, "12345678", apChannel, false, 4);
```

使用方式：

- 第一套：`RobotTimer-01`
- 第二套：`RobotTimer-02`
- 密碼可保持 `YOUR_AP_PASSWORD`
- mDNS 亦可改成 `robot-timer-01`／`robot-timer-02`

不同 AP 各自使用 192.168.4.1 不會衝突，因為手機同一時間只會連接其中一個 AP；但 SSID 必須不同，現場人員才知自己在看哪一個計時器。

## 5. Google Sheet 及結果管理

### 5.1 兩套系統使用相同卡及 Route

可共用 `CARD` 表，但 result 必須加入系統標記。最簡單是 S3 的 note 加入：

```text
SYS01,route_A,servo_command_sent
SYS02,route_B,servo_command_sent
```

更清楚的做法是把 result 欄位改成：

```text
TIMESTAMP | SYSTEM_ID | CARD NUMBER | RESULT | NOTE
```

### 5.2 兩套系統使用不同卡或 Route

建議每套系統使用自己的 Google Sheet 及自己部署的 Apps Script，避免 CARD 映射衝突。

### 5.3 Apps Script 共用

多個 S3 同時寫入 result 時，Apps Script 的 LockService 會序列化寫入，通常不會令資料損壞。但沒有 SYSTEM_ID 時，資料會混合，難以分辨。

## 6. Wi-Fi Channel 建議

如每套系統可獨立使用不同路由器／AP，可嘗試：

- 系統 1：channel 1
- 系統 2：channel 6
- 系統 3：channel 11

這樣可降低無線干擾和跨系統廣播。但若所有系統接在同一個學校 AP，channel 會相同，因此仍必須使用 `SYSTEM_ID` 過濾。

## 7. 建議現場配置

### 系統 1

```text
SYSTEM_ID = 1
AP SSID = RobotTimer-01
mDNS = robot-timer-01
Result tag = SYS01
```

### 系統 2

```text
SYSTEM_ID = 2
AP SSID = RobotTimer-02
mDNS = robot-timer-02
Result tag = SYS02
```

在實體板貼上 `SYS01`／`SYS02` 標籤，並為 USB 線、RC522、伺服及感應器分色。

## 8. 多系統測試清單

- [ ] 系統 1 拍卡：只有系統 1 WROOM 計時。
- [ ] 系統 2 拍卡：只有系統 2 WROOM 計時。
- [ ] 系統 1 按 RESET：系統 2 不重設。
- [ ] 系統 2 MOVE_180：系統 1 伺服不動作。
- [ ] 兩套同時拍卡：兩個計時器各自正常，不交換 Route。
- [ ] 兩套同時重設：各自完成，不干擾。
- [ ] 手機分別連接 RobotTimer-01／02，看到正確頁面。
- [ ] result 表可分辨 SYS01／SYS02。
- [ ] 三塊板的 SYSTEM_ID 完全一致。
- [ ] 換板或換程式後重新核對 SYSTEM_ID。

## 9. 優先次序

如時間有限，最低限度請先完成：

1. `SYSTEM_ID` 加入所有 ESP-NOW 封包及接收過濾。
2. WROOM AP 改名為 `RobotTimer-01`、`RobotTimer-02`。
3. result 加入 SYS01／SYS02 標記。

只要第 1 項未完成，就不應在同一 Wi-Fi channel 下同時運行兩套系統。
