# -*- coding: utf-8 -*-
"""輸出 Excel 報告（含原生可編輯圖表）。"""
import os
from datetime import datetime

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

FONT = "Microsoft JhengHei"
TITLE_FONT = Font(name=FONT, size=16, bold=True, color="1F3864")
SUB_FONT = Font(name=FONT, size=11, color="404040")
SECTION_FONT = Font(name=FONT, size=12, bold=True, color="1F3864")
HEAD_FONT = Font(name=FONT, size=11, bold=True, color="FFFFFF")
BODY_FONT = Font(name=FONT, size=11)
FILL_HEAD = PatternFill("solid", fgColor="2E5C8A")
FILL_SECTION = PatternFill("solid", fgColor="DCE6F1")
THIN = Side(style="thin", color="B7C6DA")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center")


def _title(ws, row, text, size=6):
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = TITLE_FONT
    return row + 1


def _subtitle(ws, row, text):
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = SUB_FONT
    return row + 1


def _section(ws, row, text, span=6):
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = SECTION_FONT
    cell.fill = FILL_SECTION
    for col in range(2, span + 1):
        ws.cell(row=row, column=col).fill = FILL_SECTION
    return row + 1


def _table(ws, row, headers, rows, widths=None, numbers=None):
    """寫入表格，回傳 (首列資料列, 最末列)。"""
    for col, head in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col, value=head)
        cell.font = HEAD_FONT
        cell.fill = FILL_HEAD
        cell.border = BORDER
        cell.alignment = CENTER
    first = row + 1
    for offset, values in enumerate(rows):
        current = first + offset
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=current, column=col, value=value)
            cell.font = BODY_FONT
            cell.border = BORDER
            cell.alignment = WRAP if col == 1 else CENTER
            if numbers and col in numbers:
                cell.number_format = numbers[col]
    if widths:
        for col, width in enumerate(widths, start=1):
            ws.column_dimensions[get_column_letter(col)].width = width
    return first, first + len(rows) - 1


def _bar(ws_src, title, header_row, last_row, data_col, cat_col, anchor, horizontal=False, width=16, height=9):
    chart = BarChart()
    chart.type = "bar" if horizontal else "col"
    chart.style = 10
    chart.title = title
    data = Reference(ws_src, min_col=data_col, min_row=header_row, max_row=last_row)
    cats = Reference(ws_src, min_col=cat_col, min_row=header_row + 1, max_row=last_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.width = width
    chart.height = height
    return chart


def build_excel(stats, advices, meta, config, path, period_label):
    thresholds = config["thresholds"]
    book = Workbook()
    summary = book.active
    summary.title = "摘要"
    summary.sheet_view.showGridLines = False

    school = config.get("school_name") or ""
    row = 1
    row = _title(summary, row, (school + " " if school else "") + config.get("report_title", "維修工程統計報告"))
    row = _subtitle(summary, row, "報告類型：%s　　期間：%s 至 %s（%d 個月）" % (
        period_label, stats["kpi"]["period_start"], stats["kpi"]["period_end"], stats["kpi"]["months"]))
    row = _subtitle(summary, row, "統計基準：申請日期　　產出時間：%s" % datetime.now().strftime("%Y-%m-%d %H:%M"))
    row = _subtitle(summary, row, "資料來源：%s（工作表：%s，共 %s 筆原始紀錄）" % (
        os.path.basename(meta["file"]), meta["sheet"], meta["valid_records"]))
    row += 1

    kpi = stats["kpi"]
    row = _section(summary, row, "一、關鍵數字")
    kpi_rows = [
        ("維修申請總數", kpi["total"], "宗"),
        ("已完成", kpi["done"], "宗"),
        ("完成率", kpi["completion_rate"], "%"),
        ("未完成（期末）", kpi["open"], "宗"),
        ("逾期未完成（超過 %d 天）" % thresholds.get("overdue_days", 30), kpi["overdue"], "宗"),
        ("平均處理天數", kpi["avg_days"], "天"),
        ("處理天數中位數", kpi["median_days"], "天"),
        ("涉及學生紀律個案", kpi["discipline"], "宗"),
    ]
    if kpi["prev_label"]:
        kpi_rows.append(("與上期比較（%s）" % kpi["prev_label"], kpi["delta_total"], "宗"))
        kpi_rows.append(("與上期比較（百分比）", kpi["delta_rate"], "%"))
    row = _table(summary, row, ["指標", "數值"], kpi_rows, widths=[46, 16])[1] + 2

    row = _section(summary, row, "二、重點建議（節錄）")
    brief = [[advice["type"], advice["title"], advice["body"]] for advice in advices[:8]]
    row = _table(summary, row, ["建議類別", "對象／題目", "建議內容"], brief,
                 widths=[46, 26, 90])[1] + 2

    row = _section(summary, row, "三、報告說明")
    notes = [
        "1. 所有統計以「申請日期」為基準；「完成」指已填寫維修完成日期或結案日期。",
        "2. 完整建議清單、各項交叉分析及個案明細，請參閱本檔案的其他工作表。",
        "3. 分類採關鍵詞字典自動判斷，未能分類的個案列於「待分類與無效紀錄」工作表，可回饋後更新分類字典。",
    ]
    for note in notes:
        row = _subtitle(summary, row, note)

    # ---------- 分類統計 ----------
    sheet = book.create_sheet("分類統計")
    sheet.sheet_view.showGridLines = False
    row = _title(sheet, 1, "維修項目分類統計")
    row += 1
    row = _section(sheet, row, "按大類")
    cat_rows = [[c["name"], c["count"], c["share"], c["done"], c["rate"], c["avg_days"], c["prev"], c["delta"]]
                for c in stats["categories"]]
    cat_header = row
    cat_first, cat_last = _table(sheet, row, ["類別", "宗數", "佔比(%)", "已完成", "完成率(%)", "平均處理天數", "上期宗數", "增減"],
                                 cat_rows, widths=[26, 10, 11, 10, 12, 14, 11, 10])
    row = cat_last + 3
    row = _section(sheet, row, "按子類（前 20 項）")
    sub_rows = [[s["name"], s["count"], s["done"], s["rate"]] for s in stats["subs"][:20]]
    _table(sheet, row, ["類別 › 子類", "宗數", "已完成", "完成率(%)"], sub_rows, widths=[46, 10, 10, 12])

    # ---------- 交叉分析 ----------
    cross = book.create_sheet("交叉分析")
    cross.sheet_view.showGridLines = False
    row = _title(cross, 1, "交叉分析")
    row += 1
    row = _section(cross, row, "按樓層")
    floor_head = row
    floor_first, floor_last = _table(cross, row, ["樓層", "宗數", "佔比(%)", "未完成"],
                                     [[f["label"], f["count"], f["share"], f["open"]] for f in stats["floors"]],
                                     widths=[26, 10, 11, 10])
    row = floor_last + 3
    row = _section(cross, row, "樓層 × 類別")
    row = _table(cross, row, ["樓層", "類別", "宗數", "涉及地點數"],
                 [[c["floor"], c["category"], c["count"], len(c["rooms"])] for c in stats.get("floor_category") or []],
                 widths=[26, 26, 10, 12])[1] + 3
    row = _section(cross, row, "按地點類型")
    row = _table(cross, row, ["地點類型", "宗數", "佔比(%)", "未完成"],
                 [[t["label"], t["count"], t["share"], t["open"]] for t in stats["types"]],
                 widths=[26, 10, 11, 10])[1] + 3
    row = _section(cross, row, "按性別")
    row = _table(cross, row, ["性別", "宗數", "佔比(%)"],
                 [[g["label"], g["count"], g["share"]] for g in stats["genders"]],
                 widths=[26, 10, 11])[1] + 3
    row = _section(cross, row, "按年級")
    row = _table(cross, row, ["年級", "宗數", "佔比(%)", "未完成"],
                 [[g["label"], g["count"], g["share"], g["open"]] for g in stats["grades"]],
                 widths=[26, 10, 11, 10])[1] + 3
    row = _section(cross, row, "按跟進人員")
    _table(cross, row, ["跟進人員", "宗數", "已完成", "平均處理天數"],
           [[s["label"], s["count"], s["done"], s["avg_days"]] for s in stats["staff"]],
           widths=[26, 10, 10, 14])

    # ---------- 房間排行 ----------
    room_sheet = book.create_sheet("房間排行")
    room_sheet.sheet_view.showGridLines = False
    row = _title(room_sheet, 1, "維修申請最多的地點")
    row += 1
    row = _section(room_sheet, row, "地點排行（前 %d 位）" % len(stats["rooms"]))
    room_head = row
    room_first, room_last = _table(room_sheet, row, ["地點", "宗數", "主要問題類別", "未完成"],
                                   [[r["label"], r["count"], r["main_category"], r["open"]] for r in stats["rooms"]],
                                   widths=[30, 10, 26, 10])
    row = room_last + 3
    row = _section(room_sheet, row, "同一地點重複出現的同類問題（需個別跟進）")
    _table(room_sheet, row, ["地點", "類別", "次數", "個案編號"],
           [[r["room"], r["category"], r["count"], "、".join(str(n) for n in r["nos"])] for r in stats["repeats"]],
           widths=[30, 26, 8, 40])

    # ---------- 趨勢 ----------
    trend = book.create_sheet("趨勢")
    trend.sheet_view.showGridLines = False
    row = _title(trend, 1, "每月申請與完成趨勢")
    row += 1
    trend_head = row
    trend_first, trend_last = _table(trend, row, ["月份", "申請宗數", "完成宗數"],
                                     [[m["month"], m["apply"], m["done"]] for m in stats["months"]],
                                     widths=[16, 12, 12])

    # ---------- 圖表 ----------
    chart_sheet = book.create_sheet("圖表")
    chart_sheet.sheet_view.showGridLines = False
    _title(chart_sheet, 1, "圖表")
    anchors = ["A3", "A24", "A45", "A66", "A88", "A110"]
    index = 0
    if stats["categories"]:
        chart_sheet.add_chart(_bar(sheet, "各類維修項目宗數", cat_header, cat_last, 2, 1,
                                   anchors[index], horizontal=True), anchors[index])
        index += 1
    if stats["months"]:
        line = LineChart()
        line.title = "每月申請與完成宗數"
        line.style = 12
        data = Reference(trend, min_col=2, max_col=3, min_row=trend_head, max_row=trend_last)
        cats = Reference(trend, min_col=1, min_row=trend_first, max_row=trend_last)
        line.add_data(data, titles_from_data=True)
        line.set_categories(cats)
        line.width, line.height = 16, 9
        chart_sheet.add_chart(line, anchors[index])
        index += 1
    if stats["rooms"]:
        chart_sheet.add_chart(_bar(room_sheet, "維修申請最多的地點", room_head, room_last, 2, 1,
                                   anchors[index], horizontal=True), anchors[index])
        index += 1
    if stats["floors"]:
        chart_sheet.add_chart(_bar(cross, "各樓層維修宗數", floor_head, floor_last, 2, 1,
                                   anchors[index], horizontal=True), anchors[index])
        index += 1
    if stats["categories"]:
        rate_rows = [[c["name"], c["rate"], c["avg_days"]] for c in stats["categories"]]
        rate_sheet = book.create_sheet("完成率數據")
        rate_sheet.sheet_view.showGridLines = False
        _title(rate_sheet, 1, "各類別完成率與平均處理天數")
        head = 3
        first, last = _table(rate_sheet, head, ["類別", "完成率(%)", "平均處理天數"], rate_rows,
                             widths=[26, 12, 14])
        chart = _bar(rate_sheet, "各類別完成率", head, last, 2, 1, anchors[index], horizontal=True)
        chart_sheet.add_chart(chart, anchors[index])
        index += 1

    # ---------- 建議清單 ----------
    advice_sheet = book.create_sheet("建議清單")
    advice_sheet.sheet_view.showGridLines = False
    row = _title(advice_sheet, 1, "建議清單（依規則自動產生，附個案編號可追溯）")
    row += 1
    advice_rows = [[advice["type"], advice["title"], advice["body"], advice["evidence"]] for advice in advices]
    _table(advice_sheet, row, ["建議類別", "對象／題目", "建議內容", "依據／個案編號"], advice_rows,
           widths=[18, 26, 80, 34])

    # ---------- 明細 ----------
    detail = book.create_sheet("明細")
    detail.sheet_view.showGridLines = False
    row = _title(detail, 1, "期內個案明細")
    row += 1
    detail_rows = []
    for record in sorted(stats["detail_records"], key=lambda r: (r["apply_date"] or datetime(1900, 1, 1).date(), r["no"])):
        detail_rows.append([
            record["no"], record["apply_date"], record["location"], record["room_code"].upper(),
            record["floor"], record["category_name"], record["sub"], record["item"], record["detail"],
            record["staff"], record["done_date"] if record["is_done"] else "未完成",
            record["days"] if record["days"] is not None else "",
            "是" if record["discipline"] else "",
        ])
    detail_first, _last = _table(detail, row,
                                 ["編號", "申請日期", "維修地點", "房號", "樓層", "類別", "子類",
                                  "維修項目", "損壞情況", "跟進人", "完成日期", "處理天數", "涉紀律"],
                                 detail_rows,
                                 widths=[7, 12, 22, 9, 9, 20, 22, 26, 34, 9, 12, 10, 8],
                                 numbers={2: "yyyy-mm-dd", 11: "yyyy-mm-dd"})
    detail.freeze_panes = detail.cell(row=detail_first, column=1)

    # ---------- 待分類與無效 ----------
    other = book.create_sheet("待分類與無效紀錄")
    other.sheet_view.showGridLines = False
    row = _title(other, 1, "待分類與無效紀錄")
    row += 1
    row = _section(other, row, "未能自動分類（建議確認後加入分類字典）")
    row = _table(other, row, ["編號", "維修地點", "維修項目", "損壞情況"],
                 [[r["no"], r["location"], r["item"], r["detail"]] for r in stats["unclassified"]],
                 widths=[8, 24, 30, 40])[1] + 3
    row = _section(other, row, "無效或測試紀錄")
    _table(other, row, ["編號", "維修地點", "維修項目", "損壞情況"],
           [[r["no"], r["location"], r["item"], r["detail"]] for r in stats["invalid_records"]],
           widths=[8, 24, 30, 40])

    book.save(path)
    return path
