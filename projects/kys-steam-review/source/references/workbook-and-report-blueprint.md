# Workbook and Report Blueprint

## 1. Workbook purpose

Produce one editable `.xlsx` that lets a school leader:

- see the overall STEAM position in one view;
- compare subjects fairly;
- trace every number back to a source activity;
- understand the strategic direction and phased actions;
- verify sources and limitations.

Use the Spreadsheets skill and `@oai/artifact-tool`. Keep the workbook simple enough to navigate but detailed enough to audit.

## 2. Required sheets

### `總覽`

Include:

- title with school year and extraction date;
- seven KPI cards: plan files, active subjects, activity records, unique themes, cross-subject records, average elements, substantive reviews;
- five current-state judgments;
- five strategic directions;
- four charts;
- source/duplicate/limitation note.

Recommended charts:

1. `各科活動紀錄數` — horizontal bar.
2. `STEAM 元素覆蓋（活動紀錄）` — column/bar for S, T, E, A, M.
3. `實施特徵（可重疊計）` — horizontal bar for hands-on, digital/AI, real-world, Technology for Good, competition/certification, product evidence.
4. `活動類型分佈（科組紀錄）` — doughnut or pie.

Keep chart text concise and add a note that charts use subject-reported records, not deduplicated themes.

### `科目總覽`

One row per subject panel. Recommended columns:

- 科組
- 代碼
- 活動紀錄
- 去重主題
- S / T / E / A / M counts
- 元素廣度
- 跨科紀錄
- 動手實作
- 數碼/AI
- 真實情境
- 科技向善
- 平均元素
- 成熟度
- 優先方向

Add totals and a short maturity-definition note. Use data bars for activity count and light fills for non-zero element counts.

### `活動明細`

One row per subject-reported record. Recommended columns:

- `#`
- 科組
- 原代號
- 月份
- 活動主題
- 目的
- 內容/形式
- 級別
- S / T / E / A / M
- 元素數
- 跨科
- 合作科組
- 動手實作
- 數碼/AI
- 真實情境
- 科技向善
- 評估方法
- 活動類型
- 來源檔案
- 來源工作表 / 行號

Use an Excel table with filters, frozen header row and subject columns, wrapped text, and row-height estimation based on the longest `目的`, `內容`, and `評估方法` fields.

### `分析數據`

Keep chart-source tables and formula/calculation notes. Include:

- KPI table
- element coverage
- feature counts
- activity categories
- maturity counts
- subject chart data

### `總結報告`

Recommended structure:

1. 範圍與方法
2. 總體現況
3. 主要發現 — 優勢 and 待改善
4. 策略方向 — EDB reference, current position, next action
5. 優先建議 — 0–3 months, 3–12 months, 12–24 months
6. 建議 KPI
7. 科目分層行動
8. 結論

Use dense but readable tables for the strategic direction and KPI sections. The conclusion should state the central shift: from scattered activities to curriculum-embedded, repeatable, assessable cross-disciplinary learning.

### `資料來源`

Include:

- source-file list with subject panel and activity count;
- source row references;
- EDB URL and key points;
- extraction and deduplication methodology;
- limitations.

## 3. Visual system

Use a restrained palette:

- navy `#0B1F33` for titles and headers;
- teal `#0F766E` for primary accents;
- blue `#2563EB` for data and digital themes;
- amber `#D97706` for cautions and recommendations;
- green `#166534` for strengths;
- red `#B91C1C` for gaps and unfilled subjects;
- light fills for cards and alternating rows.

Use `Microsoft JhengHei` for Traditional Chinese. Keep all gridlines off on presentation sheets. Set readable column widths and wrapped text.

## 4. Report language

Use direct, decision-oriented headings. Avoid generic statements such as “STEAM is important.” Every paragraph should do one of the following:

- describe a measured condition;
- explain why it matters;
- identify a design gap;
- propose an observable action;
- define how success will be measured.

Distinguish:

- participation vs depth;
- subject-level record vs unique theme;
- activity type vs learning quality;
- claimed element coverage vs demonstrated learning;
- plan implementation vs impact.

## 5. Verification

Before delivery:

1. Check sheet names, chart count, table ranges, and row counts.
2. Confirm each chart references the intended analysis range.
3. Check for `#REF!`, `#VALUE!`, `#DIV/0!`, `#NAME?`, and other obvious errors.
4. Use layout export or rendering to detect text overflow and chart overlap.
5. If the model cannot directly inspect images, export layout data and calculate text-fit heuristics using cell/merged width, height, font size, and wrapped text.
6. Confirm the dashboard does not overlap charts or notes.
7. Confirm the final report contains source and limitation statements.

## 6. Deliverable placement

Save the final workbook under the task's `outputs/` directory unless the user specifies another location. Do not expose builder scripts or preview files in the final answer unless requested.