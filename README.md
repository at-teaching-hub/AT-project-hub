# AT Project Hub

- GitHub: <https://github.com/at-teaching-hub/AT-project-hub>
- GitHub Pages: <https://at-teaching-hub.github.io/AT-project-hub/>

公開展示經檢查及去敏感的精選項目。

## 公開項目

| 項目 | 類型 | 入口 |
|---|---|---|
| 四足拔河模擬器 | HTML 模擬器 | `projects/tug-of-war-simulator/` |
| 機械人奪寶奇兵比賽系統 | ESP32 + Apps Script | `projects/robot-competition-system/` |
| ESP32-C3 座椅壓力感測器 | Arduino | `projects/esp32-pressure-sensor/` |
| 2027 STEAM 機械人比賽簡介 | PowerPoint | `projects/competition-presentation/` |

## 發佈規則

- 公開版本不含真實 Wi-Fi 密碼、API Token、Apps Script 部署網址、教師／學生個人資料或學校內部文件。
- 其餘項目存放於 [AT-private-archive](https://github.com/at-teaching-hub/AT-private-archive)，只可維持 Private。
- 青瓷迷你花瓶已按指示從公開及私人發佈範圍取消；本機原始檔仍保留。
- 每次新增項目時，先判斷是否含個人、學校、客戶或部署資料；如不確定，預設放入私人封存庫。

## 網頁入口

`index.html` 是靜態入口頁，由 GitHub Pages 自動部署。搜尋與篩選在瀏覽器端執行。

## 更新與發佈

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check-sensitive.ps1
powershell -ExecutionPolicy Bypass -File scripts/publish.ps1 -Message "Update projects"
```

## 自動化

Codex Automation「AT GitHub 每日同步」已啟用，每日 18:00 會：

1. 同步私人封存並推送至 `AT-private-archive`。
2. 檢查公開內容敏感資料，然後提交及推送至 `AT-project-hub`。
3. GitHub Actions 自動重新部署 GitHub Pages。

失敗時才會通知；手動執行可使用：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/publish.ps1 -Message "Update projects"
```