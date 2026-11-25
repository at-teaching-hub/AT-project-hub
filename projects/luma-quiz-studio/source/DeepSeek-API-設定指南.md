# 知光 Luma｜DeepSeek API 設定指南

## 架構
- 教師頁只負責提交筆記、題型和題量。
- Apps Script 在後端呼叫 DeepSeek API。
- API Key 儲存在 Apps Script 的指令碼屬性，不會放入學生頁面。
- AI 回傳結構化題目後，老師應先預覽來源句子、答案及評分。

官方 API 文件：
- https://api-docs.deepseek.com/api/create-chat-completion/
- https://api-docs.deepseek.com/guides/responses_api/

預設呼叫：
```text
POST https://api.deepseek.com/chat/completions
Authorization: Bearer <DEEPSEEK_API_KEY>
```

## 第 1 步：取得 DeepSeek API Key
在 DeepSeek 開發者平台建立 API Key。不要把 Key 貼在聊天、HTML、Google Sheet 或學生可見的位置。

## 第 2 步：更新 Apps Script
1. 以最新 `apps-script-hosted/Code.gs` 取代 Apps Script 的 `Code.gs`。
2. 以最新 `apps-script-hosted/Index.html` 取代 `Index.html`。
3. 按 `Ctrl + S` 儲存。

## 第 3 步：設定 Script Properties
1. Apps Script 左側按「專案設定 / Project Settings」。
2. 找到「指令碼屬性 / Script Properties」。
3. 新增以下屬性：

| 屬性名稱 | 值 | 是否必要 |
|---|---|---|
| `DEEPSEEK_API_KEY` | 你的 DeepSeek API Key | 必要 |
| `DEEPSEEK_MODEL` | `deepseek-flash` 或其他帳戶可用模型 | 建議 |
| `DEEPSEEK_API_URL` | 預設 `https://api.deepseek.com/chat/completions` | 選填 |
| `LUMA_AI_TOKEN` | 自行設定的長隨機英數字，例如 32 位以上 | 必要 |

4. 儲存。
5. 回到 Luma 教師頁，按右上角齒輪開啟設定，在「DeepSeek AI 存取碼」輸入與 `LUMA_AI_TOKEN` **完全相同**的字串，再按儲存。

`LUMA_AI_TOKEN` 不是 DeepSeek API Key，它用來防止學生或公眾直接觸發 AI 出題功能。

## 第 4 步：授權外部請求
1. 上方函式下拉選單選擇 `authorizeLumaServices`。
2. 按「執行 / Run」。
3. 選擇 Google 帳戶並允許要求的權限。
4. 確認執行記錄顯示 `Luma external request authorization ready`。

此步驟只授權 Apps Script 向外部 API 發出請求，不會呼叫生成題目。

## 第 5 步：部署新版本
1. 按「部署 / Deploy」。
2. 選擇「管理部署 / Manage deployments」。
3. 按現有部署旁的鉛筆圖示。
4. 版本選擇「新版本 / New version」。
5. 按「部署 / Deploy」。

只按 `Ctrl + S` 不會更新公開網站。

## 第 6 步：在 Luma 使用 AI 出題
1. 開啟教師入口。
2. 前往「建立考卷」。
3. 選擇筆記、題型及題目數量。
4. 按「DeepSeek 生成」。
5. 等待生成完成。
6. 查看每題下方的「來源」句子。
7. 校對題目、選項、答案及分數後再發佈。

## AI 會使用的資料
只會傳送：
- 筆記標題
- 學習點
- 筆記文字
- 已選題型及題量

不會傳送：
- 學生姓名
- 班別或班號
- 成績或提交記錄

## 常見錯誤
### `DEEPSEEK_API_KEY 尚未設定`
請回到「專案設定 › 指令碼屬性」加入 `DEEPSEEK_API_KEY`。

### `DeepSeek API 回應錯誤（401）`
API Key 不正確或已失效，請重新建立 Key 並更新指令碼屬性。

### `DeepSeek API 回應錯誤（402）`
DeepSeek 帳戶餘額不足。

### `DeepSeek API 回應錯誤（429）`
請求太頻密或已超出限額，請稍後再試。

### `DeepSeek 回傳的題目 JSON 格式不正確`
系統已啟用 JSON Output；如仍出現，請重試一次。若持續發生，可改用另一個已支援 JSON Output 的模型。

### `AI 生成失敗`
先確認：
1. 已執行 `authorizeLumaServices`。
2. 已設定 `DEEPSEEK_API_KEY`。
3. 已部署新版本。
4. `Index.html` 和 `Code.gs` 都是最新版本。

