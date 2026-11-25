# Codex Project Hub

把歷次製作的應用程式、HTML、模擬器、物聯網程式、簡報、3D 資產與 Codex Skill 集中在一個可修訂、可搜尋及可公開展示的倉庫。

## 公開項目

| 項目 | 類型 | 入口 |
|---|---|---|
| 四足拔河模擬器 | HTML 模擬器 | `projects/tug-of-war-simulator/` |
| 維修工程統計報告產生器 | Python App | `projects/maintenance-report-tool/` |
| 知光 Luma 網上測驗卷工具 | HTML + Apps Script | `projects/luma-quiz-studio/` |
| 機械人奪寶奇兵比賽系統 | ESP32 + Apps Script | `projects/robot-competition-system/` |
| ESP32-C3 座椅壓力感測器 | Arduino | `projects/esp32-pressure-sensor/` |
| 2027 STEAM 機械人比賽簡介 | PowerPoint | `projects/competition-presentation/` |
| 青瓷迷你花瓶 | Blender | `projects/celadon-vase/` |
| KYS STEAM 課程檢視 | Codex Skill | `projects/kys-steam-review/` |

## 公開與私人分流

- **公開版本**：不含真實 Wi-Fi 密碼、API Token、Apps Script 部署網址、教師／學生個人資料或學校內部文件。
- **私人封存庫**：保存在本機 `outputs/codex-private-archive/`，只應推送至 **Private GitHub repository**。
- 每次新增項目時，先判斷是否含個人、學校、客戶或部署資料；如不確定，預設放入私人封存庫。

## 網頁入口

`index.html` 是靜態入口頁，可由 GitHub Pages 自動部署。搜尋與篩選在瀏覽器端執行，不需要後端。

## 更新與發佈

```powershell
# 檢查敏感內容
powershell -ExecutionPolicy Bypass -File scripts/check-sensitive.ps1

# 提交及推送
powershell -ExecutionPolicy Bypass -File scripts/publish.ps1 -Message "Update projects"
```

首次發佈前，請先在 GitHub 建立同名 repository，並設定 remote `origin`。GitHub Actions 會在推送後自動部署 Pages。

## 新增項目

1. 在 `projects/<slug>/` 建立項目資料夾。
2. 將可公開的程式與說明放入 `source/`。
3. 在 `index.html` 及本 README 加入項目入口。
4. 執行 `scripts/check-sensitive.ps1`。
5. 執行 `scripts/publish.ps1`。

## 授權

各項目可能使用不同授權。未附 `LICENSE` 的內容預設保留所有權利；如需開放再利用，請按項目另行加入授權。

## 自動化

審核後的公開內容可按需要安裝 Windows 每日排程：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install-scheduled-publish.ps1 -Time 18:10
```

排程只會提交並推送 **已放入本倉庫且已通過敏感掃描** 的內容；不會自動把 Documents\Codex 的所有新檔案公開，以免誤傳個人或學校資料。