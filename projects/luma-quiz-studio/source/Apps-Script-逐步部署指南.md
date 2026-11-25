# 知光 Luma｜Google Apps Script 逐步部署指南

> 目標：把同一個 Apps Script Web App 同時用作「測驗網站」和「Google Sheet API」。完成後毋須另找網站寄存。

## 開始前
1. 下載並解壓 `luma-final-package-v3.zip`。
2. 開啟資料夾 `apps-script-hosted`。
3. 你會使用以下兩個檔案：
   - `Code.gs`
   - `Index.html`

請注意：`Index.html` 必須貼入 Apps Script 的 **HTML 檔案**，不是貼在 `Code.gs`。

---

## 第 1 步：開啟 Apps Script
1. 開啟你的 Google Sheet。
2. 按「擴充功能 / Extensions」。
3. 按「Apps Script」。
4. 確認進入與這份 Google Sheet 連結的 Apps Script 專案。

---

## 第 2 步：替換 Code.gs
1. 在左側「檔案 / Files」按 `Code.gs`。
2. 在編輯器中按 `Ctrl + A` 全選。
3. 刪除原有程式碼。
4. 開啟本機 `apps-script-hosted/Code.gs`。
5. 全選並複製檔案內全部內容。
6. 貼到 Apps Script 的 `Code.gs`。
7. 按 `Ctrl + S` 儲存。

### 成功檢查
`Code.gs` 最上方應看到 `function setup()`，而且應有：
- `doGet`
- `doPost`
- `HtmlService.createHtmlOutputFromFile('Index')`

---

## 第 3 步：新增 Index HTML 檔案
1. 在左側「檔案 / Files」右邊按 `+`。
2. 選擇「HTML / HTML 檔案」。
3. 檔名輸入 `Index`，不要自行輸入 `.html`。Apps Script 會顯示為 `Index.html`。
4. 如果已經有 `Index.html`，直接開啟舊檔取代內容，不要建立第二個同名檔案。
5. 開啟本機 `apps-script-hosted/Index.html`。
6. 全選並複製全部內容。
7. 貼入 Apps Script 的 `Index.html`。
8. 按 `Ctrl + S` 儲存。

### 成功檢查
左側應同時有：
- `Code.gs`
- `Index.html`

---

## 第 4 步：執行 setup()
1. 在 Apps Script 上方的函式下拉選單選擇 `setup`。
2. 按「執行 / Run」。
3. 選擇你的 Google 帳戶。
4. 如出現「Google 尚未驗證這個應用程式」：
   - 按「進階 / Advanced」。
   - 按「前往專案（不安全） / Go to project (unsafe)」。
   - 查看權限並按「允許 / Allow」。
5. 確認執行記錄顯示 `Luma sheets ready`。

`setup()` 會整理分頁第一列欄位，但**不會清空第一列以下的資料**。

### 應存在的分頁
- `Students`
- `Submissions`
- `QuestionBank`
- `Notes`
- `Quizzes`

---

## 第 5 步：更新現有部署
如你之前已部署過 Web App：

1. 按右上角「部署 / Deploy」。
2. 選擇「管理部署 / Manage deployments」。
3. 在目前部署旁邊按鉛筆圖示。
4. 版本 / Version 選擇「新版本 / New version」。
5. 按「部署 / Deploy」。
6. 不要建立另一個新部署，否則網址可能改變。

### 如從未部署
1. 按「部署 / Deploy」。
2. 選擇「新增部署 / New deployment」。
3. 按齒輪，選擇「網頁應用程式 / Web app」。
4. 執行身分 / Execute as：`我 / Me`
5. 誰有存取權 / Who has access：`任何人 / Anyone`
6. 按「部署 / Deploy」。
7. 複製 Web App URL。

---

## 第 6 步：測試教師入口
在瀏覽器開啟：

```text
https://script.google.com/macros/s/你的部署ID/exec
```

應看到「知光 Luma」教師工作台。

如果仍看到：

```json
{"ok":true,"service":"Luma Quiz Sync"}
```

代表瀏覽器仍在用舊版本。請回到「管理部署」確認已用新版本重新部署。

---

## 第 7 步：測試學生入口
在網址末端加入：

```text
?mode=student
```

完整例子：

```text
https://script.google.com/macros/s/你的部署ID/exec?mode=student
```

應直接看到學生登入頁，不會顯示「教師模式」按鈕。
選擇班別及輸入班號後，系統應自動顯示學生姓名。

---

## 第 8 步：測試名單 API
開啟：

```text
https://script.google.com/macros/s/你的部署ID/exec?action=roster
```

應顯示「Luma 名單接口已連線」及讀取到的學生人數。
這個頁面只供檢查系統連線，不需分享給學生。

如要檢查原始 JSON，可開啟：

```text
https://script.google.com/macros/s/你的部署ID/exec?action=roster&format=json
```

應用程式會在背景使用這個 JSON 版本讀取學生姓名。

---

## 第 9 步：檢查提交記錄
1. 以一位測試學生完成並呈交測驗。
2. 回到 Google Sheet。
3. 開啟 `Submissions` 分頁。
4. 應新增一列，包含：
   - 呈交時間
   - 班別及班號
   - 學生姓名
   - 分數及評級
   - 開始時間及用時
   - Answers JSON
   - Review JSON

如同時需要測試教師名單，請使用測試班別或測試學生，避免把測試作答混入正式成績。

---

## DeepSeek AI 出題設定
1. 到 Apps Script「專案設定 / Project Settings」。
2. 在「指令碼屬性 / Script Properties」新增：
   - `DEEPSEEK_API_KEY`：你的 DeepSeek API Key
   - `DEEPSEEK_MODEL`：例如 `deepseek-flash`
   - `LUMA_AI_TOKEN`：自行設定的長隨機英數字
3. 在上方函式選單執行 `authorizeLumaServices` 一次，按提示允許外部請求。
4. 更新部署至新版本。
5. 回到 Luma 設定頁，在「DeepSeek AI 存取碼」輸入相同的 `LUMA_AI_TOKEN`。
6. 在「建立考卷」按「DeepSeek 生成」。

API Key 只會保存在 Apps Script，不會傳到學生頁面。詳細說明見 `DeepSeek-API-設定指南.md`。
## 常見問題

### 1. 根網址仍顯示 JSON
原因：
- `Index.html` 未建立或檔名不正確。
- `Code.gs` 未貼上最新版本。
- 只儲存了程式碼，但未部署「新版本」。

處理：
1. 確認左側有 `Index.html`。
2. 確認 `Code.gs` 含有 `HtmlService.createHtmlOutputFromFile('Index')`。
3. 重新執行「管理部署 › 編輯 › 新版本 › 部署」。

### 2. Cannot find Index
表示 HTML 檔名不是 `Index`。請改名為 `Index`，不要使用 `index.html.html`。

### 3. 學生入口顯示教師工作台
確認網址有 `?mode=student`，例如：

```text
.../exec?mode=student
```

### 4. 學生看不到姓名
1. 確認 `Students` 分頁第一列是 `Class,Number,Name`。
2. 確認班別和班號格式與名單一致。
3. 開啟 `?action=roster` 確認顯示「名單接口已連線」；程式會使用 `?action=roster&format=json`。
4. 如果最近上載了新名單，重新整理學生頁面。

### 5. 提交後 Google Sheet 沒有新記錄
1. 確認 `Submissions` 分頁存在。
2. 確認部署存取權是「任何人」。
3. 確認 `Code.gs` 的 `doPost` 仍在。
4. 在開發人員工具檢查網絡請求是否失敗；如失敗，成績仍會暫存在學生本機。

### 6. 對程式碼做了修改但網站沒有更新
必須重新部署新版本：
`部署 › 管理部署 › 編輯目前部署 › 新版本 › 部署`。

只按 `Ctrl + S` 不會自動更新已發佈的網址。

---

## 完成後的連結
### 教師
```text
https://script.google.com/macros/s/你的部署ID/exec
```

### 學生
```text
https://script.google.com/macros/s/你的部署ID/exec?mode=student
```

建議把學生連結以 QR Code 或班級平台分享，教師連結則只發給教師。




