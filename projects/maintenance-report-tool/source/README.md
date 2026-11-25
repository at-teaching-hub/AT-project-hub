# SCR 維修工程統計報告產生器

為學校維修工程項目自動產生 **季報** 與 **年報**，輸出 Excel（含可編輯圖表）、Word 及 PDF 三種格式。

資料來源：你上傳的維修申請表（Google Sheet 匯出的 **.xlsx / .xls / .csv**）。
統計基準：**申請日期**。
季報固定為 **9–12 月 / 1–4 月 / 5–8 月**；年報為 **9 月–翌年 8 月**。

---

## 一、安裝（只需做一次）

1. 安裝 Python 3.9 或以上：<https://www.python.org/downloads/>（安裝時**必須**勾選 Add python.exe to PATH）
2. 雙擊 **install_deps.bat** 安裝所需套件（pandas、openpyxl、xlrd、matplotlib、python-docx、reportlab）

## 二、每次產生報告

1. 把最新的維修表檔案放在任何位置。
2. 雙擊 **run.bat**，按畫面指示輸入：
   - 檔案路徑（可直接把檔案**拖入**視窗）
   - 報告類型：1 = 9–12 月、2 = 1–4 月、3 = 5–8 月、4 = 年報、5 = 自訂期間
   - 學年起始年份（例如 **2025** 代表 2025–26 學年）
3. 完成後，`outputs` 資料夾會出現：
   - `維修工程報告_季報_2025-09_2025-12.xlsx`（Excel）
   - `維修工程報告_季報_2025-09_2025-12.docx`（Word）
   - `維修工程報告_季報_2025-09_2025-12.pdf`（PDF）
   - `維修工程報告_季報_2025-09_2025-12_圖表`\（PNG 圖表）

### 指令模式（方便自行寫批次檔）

```
python src/main.py --file "維修表.xlsx" --type 季報 --season 1 --year 2025
python src/main.py --file "維修表.xlsx" --type 季報 --season 2 --year 2025     # 1–4 月
python src/main.py --file "維修表.xlsx" --type 年報 --year 2025
python src/main.py --file "維修表.xlsx" --type 自訂 --start 2025-09 --end 2026-01
python src/main.py --file "維修表.xlsx" --list-sheets      # 查看檔案有哪些工作表
python src/main.py --file "維修表.xlsx" --formats pdf       # 只出 PDF
python src/main.py --file "維修表.xlsx" --no-compare        # 不做上期比較
```

---

## 三、報告內容

### Excel

| 工作表 | 內容 |
|---|---|
| 摘要 | 關鍵數字、重點建議節錄、報告說明 |
| 分類統計 | 11 大類統計（宗數／佔比／完成率／平均處理天數／上期比較）＋ 子類前 20 |
| 交叉分析 | 樓層、樓層 × 類別、地點類型、性別、年級、跟進人員 |
| 房間排行 | 各房間／地點排行 ＋ 同房同類重複個案（需個別跟進） |
| 趨勢 | 每月申請與完成宗數 |
| 圖表 | Excel 原生折線圖及條形圖（可直接修改） |
| 建議清單 | 每項建議附「觸發依據／個案編號」 |
| 明細 | 期內所有個案（可篩選） |
| 待分類與無效紀錄 | 需人工確認的個案 |

### Word / PDF

一、摘要（關鍵數字＋趨勢圖）　二、維修項目分類統計　三、趨勢與效率　四、地點分析　五、性別與年級分析　六、建議　七、附錄：待分類與無效紀錄

### 建議類別（每項皆附個案編號可追溯）

觀察（整體／分類／趨勢／時間／效率）· **個別跟進** · **部份更換** · **全面更換** · **個別房間建議** · **個別樓層建議** · **男生／女生建議** · **不同年級建議** · 其他建議（風險／逾期跟進／資料品質）

---

## 四、統計規則

- **申請宗數**：以「時間戳記（申請日期）」落在報告期間內計算。
- **完成宗數（期內完成）**：以「維修完成日期」或「結案日期」落在期間內計算，故與申請宗數不同屬正常。
- **已完成／未完成**：有維修完成日期或結案日期即視為已完成。
- **完成率** = 已完成 ÷ 申請宗數。
- **平均／中位處理天數** = 維修完成日期 − 申請日期（僅計已完成個案）。
- **逾期未完成**：未完成且申請日距今超過 `overdue_days`（預設 30 天）。
- **上期**：自動取性質相同的上一期間（季報 → 上一季；年報 → 上一年；自訂 → 相同月數的上一段期間）。
- **測試紀錄**（例如 test、如圖）不計入統計，只列於附錄。

---

## 五、調整設定（不用改程式）

| 想改的東西 | 檔案 | 說明 |
|---|---|---|
| 校名、報告標題 | `config/settings.json` → school_name、report_title | 校名會顯示在報告抬頭 |
| 建議門檻 | `config/settings.json` → thresholds | overdue_days、repeat_cases_min、partial_replace_min、full_replace_min、room_alert_min、grade_alert_min、floor_share_alert |
| 風險關鍵詞 | `config/settings.json` → risk_keywords | 自訂風險分類與關鍵詞 |
| **維修項目分類** | `config/classification.json` | 加入／修改關鍵詞；groups = 每個關鍵詞組至少命中一個，none = 命中即排除；順序 = 優先次序 |
| 位置／年級對照 | `config/rooms.json` | 由 kys_room.xlsx 產生，可用 `python src/build_rooms.py --file "kys_room.xlsx"` 重建 |
| 欄位名稱對應 | `config/settings.json` → column_map | 若 Google Sheet 表頭改名，在此調整 |

### 提高分類準確度的流程

1. 每次產生報告後，打開 Excel 的「**待分類與無效紀錄**」工作表。
2. 把未分類個案的關鍵詞加入 `classification.json` 對應的子類。
3. 下次統計即會自動歸類（現有 424 宗資料已校準，自動分類率約 99%）。

---

## 六、檔案結構

```
maintenance-report-tool/
├─ run.bat                 互動式執行（雙擊）
├─ run_example.bat         把維修表拖到此檔案，即產生 2025-26 第一季報告
├─ install_deps.bat        安裝所需套件
├─ requirements.txt
├─ config/
│   ├─ settings.json       期間、門檻、欄位對應、風險關鍵詞
│   ├─ classification.json 維修項目分類字典
│   └─ rooms.json          位置／樓層／年級對照（由 kys_room.xlsx 產生）
├─ src/
│   ├─ main.py             CLI 入口（含互動模式）
│   ├─ loader.py           讀取 xlsx / xls / csv
│   ├─ cleaning.py         日期、地點、狀態清洗
│   ├─ rooms.py            位置索引
│   ├─ classifier.py       分類引擎
│   ├─ analyzer.py         統計分析
│   ├─ advisor.py          建議引擎
│   ├─ charts.py           圖表（matplotlib）
│   ├─ report_excel.py     Excel 輸出
│   ├─ report_word.py      Word 輸出
│   ├─ report_pdf.py       PDF 輸出
│   ├─ build_rooms.py      重建 rooms.json
│   └─ textutil.py         文字工具
└─ outputs/                報告輸出位置
```

---

## 七、常見問題

**Q：Word／PDF 的中文顯示成方框？**
程式會自動尋找微軟正黑體（msjh.ttc）、細明體（mingliu.ttc）；若電腦沒有，可安裝「微軟正黑體」，或在 `charts.py` 的 _FONT_CANDIDATES 加入你的字型檔名。

**Q：Excel 日期顯示為數字（例如 45894）？**
程式已自動把 Excel 序號轉為日期，毋須手動處理。

**Q：出現「只配對到 N 個欄位」警告？**
表示表頭與預設不同：用 `--list-sheets` 查看工作表名稱，再調整 `settings.json` 的 column_map／sheet_candidates。

**Q：期末未完成個案很多，完成率偏低？**
屬正常現象——報告按「申請日期」統計，仍在處理的個案會計入未完成，並列於「逾期未完成」。

**Q：想改季度定義（例如改成 9–11 月）？**
修改 `config/settings.json` 的 periods.quarterly，以及 `src/main.py` 的 resolve_period 對應月份。
