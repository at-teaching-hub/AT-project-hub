# -*- coding: utf-8 -*-
"""輸出 Word（.docx）報告。"""
import os
from datetime import datetime

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = "Microsoft JhengHei"
NAVY = "1F3864"


def _set_default_font(doc, name=FONT):
    style = doc.styles["Normal"]
    style.font.name = name
    style.font.size = Pt(10.5)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), name)


def _para(doc, text, size=10.5, bold=False, color=None, align=None, space_after=4, space_before=0):
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    if align == "center":
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(space_after)
    paragraph.paragraph_format.space_before = Pt(space_before)
    return paragraph


def _heading(doc, text):
    return _para(doc, text, size=13, bold=True, color=NAVY, space_before=10, space_after=6)


def _table(doc, headers, rows, widths=None, font_size=9.5):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for index, head in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell.text = ""
        run = cell.paragraphs[0].add_run(str(head))
        run.bold = True
        run.font.size = Pt(font_size)
    for values in rows:
        cells = table.add_row().cells
        for index, value in enumerate(values):
            cells[index].text = ""
            run = cells[index].paragraphs[0].add_run("" if value is None else str(value))
            run.font.size = Pt(font_size)
    if widths:
        for row in table.rows:
            for index, width in enumerate(widths):
                if index < len(row.cells):
                    row.cells[index].width = Cm(width)
    return table


def _picture(doc, path, width_cm=16.0):
    if path and os.path.exists(path):
        doc.add_picture(path, width=Cm(width_cm))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def build_word(stats, advices, meta, config, path, period_label, chart_paths):
    doc = Document()
    _set_default_font(doc)
    section = doc.sections[0]
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)

    school = config.get("school_name") or ""
    _para(doc, (school + " " if school else "") + config.get("report_title", "維修工程統計報告"),
          size=20, bold=True, color=NAVY, align="center", space_after=6)
    _para(doc, "%s　　期間：%s 至 %s" % (period_label, stats["kpi"]["period_start"], stats["kpi"]["period_end"]),
          size=12, align="center", space_after=2)
    _para(doc, "統計基準：申請日期　　產出時間：%s" % datetime.now().strftime("%Y-%m-%d %H:%M"),
          size=10, align="center", color="595959", space_after=2)
    _para(doc, "資料來源：%s（工作表：%s）" % (os.path.basename(meta["file"]), meta["sheet"]),
          size=10, align="center", color="595959", space_after=10)

    kpi = stats["kpi"]
    _heading(doc, "一、摘要")
    _table(doc, ["指標", "數值", "指標", "數值"], [
        ["維修申請總數", "%d 宗" % kpi["total"], "已完成", "%d 宗" % kpi["done"]],
        ["完成率", "%.1f%%" % kpi["completion_rate"], "未完成（期末）", "%d 宗" % kpi["open"]],
        ["逾期未完成", "%d 宗" % kpi["overdue"], "平均處理天數", "%.1f 天" % kpi["avg_days"]],
        ["處理天數中位數", "%.1f 天" % kpi["median_days"], "涉及學生紀律", "%d 宗" % kpi["discipline"]],
        ["與上期比較", "%+d 宗（%+.1f%%）" % (kpi["delta_total"], kpi["delta_rate"]) if kpi["prev_label"] else "—",
         "上期期間", kpi["prev_label"] or "—"],
        ["最繁忙月份", kpi["busiest_month"] or "—", "期內完成宗數", "%d 宗" % kpi["done_in_period"]],
    ], widths=[3.4, 4.0, 3.6, 4.0])
    _picture(doc, chart_paths.get("monthly"), 16.0)

    _heading(doc, "二、維修項目分類統計")
    _table(doc, ["類別", "宗數", "佔比", "已完成", "完成率", "平均處理天數", "上期", "增減"],
           [[c["name"], c["count"], "%.1f%%" % c["share"], c["done"], "%.1f%%" % c["rate"],
             "%.1f" % c["avg_days"], c["prev"], "%+d" % c["delta"]] for c in stats["categories"]],
           widths=[3.4, 1.4, 1.5, 1.5, 1.6, 2.0, 1.4, 1.4])
    _picture(doc, chart_paths.get("category"), 16.0)
    if stats["subs"]:
        _para(doc, "主要子類（前 10 項）", size=10.5, bold=True, space_before=6, space_after=4)
        _table(doc, ["類別 › 子類", "宗數", "已完成", "完成率"],
               [[s["name"], s["count"], s["done"], "%.1f%%" % s["rate"]] for s in stats["subs"][:10]],
               widths=[8.5, 2.0, 2.0, 2.5])

    _heading(doc, "三、趨勢與效率")
    _table(doc, ["月份", "申請宗數", "完成宗數"],
           [[m["month"], m["apply"], m["done"]] for m in stats["months"]],
           widths=[4.0, 3.0, 3.0])
    _picture(doc, chart_paths.get("efficiency"), 16.0)

    _heading(doc, "四、地點分析")
    _table(doc, ["樓層", "宗數", "佔比", "未完成"],
           [[f["label"], f["count"], "%.1f%%" % f["share"], f["open"]] for f in stats["floors"]],
           widths=[4.5, 2.5, 2.5, 2.5])
    _picture(doc, chart_paths.get("floor"), 16.0)
    _para(doc, "維修申請最多的地點", size=10.5, bold=True, space_before=6, space_after=4)
    _table(doc, ["地點", "宗數", "主要問題類別", "未完成"],
           [[r["label"], r["count"], r["main_category"], r["open"]] for r in stats["rooms"]],
           widths=[6.0, 2.0, 5.5, 2.5])
    _picture(doc, chart_paths.get("room"), 16.0)
    if stats["repeats"]:
        _para(doc, "同一地點重複出現的同類問題（需個別跟進）", size=10.5, bold=True, space_before=6, space_after=4)
        _table(doc, ["地點", "類別", "次數", "個案編號"],
               [[r["room"], r["category"], r["count"], "、".join(str(n) for n in r["nos"])] for r in stats["repeats"][:15]],
               widths=[5.0, 4.5, 1.5, 5.0])

    _heading(doc, "五、性別與年級分析")
    _picture(doc, chart_paths.get("gender_grade"), 16.0)
    if stats["genders"]:
        _table(doc, ["性別", "宗數", "佔比"],
               [[g["label"], g["count"], "%.1f%%" % g["share"]] for g in stats["genders"]],
               widths=[4.0, 3.0, 3.0])
    if stats["grades"]:
        _table(doc, ["年級", "宗數", "佔比", "未完成"],
               [[g["label"], g["count"], "%.1f%%" % g["share"], g["open"]] for g in stats["grades"]],
               widths=[4.0, 3.0, 3.0, 3.0])

    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    _heading(doc, "六、建議")
    _para(doc, "以下建議由系統按既定規則自動產生，每項均附觸發依據或個案編號，方便核實與跟進。",
          size=10, color="595959", space_after=6)
    for advice in advices:
        _para(doc, "【%s】%s" % (advice["type"], advice["title"]), size=10.5, bold=True, space_before=6, space_after=2)
        _para(doc, advice["body"], size=10.5, space_after=2)
        if advice["evidence"]:
            _para(doc, advice["evidence"], size=9, color="7F7F7F", space_after=4)

    _heading(doc, "七、附錄：待分類與無效紀錄")
    if stats["unclassified"]:
        _table(doc, ["編號", "維修地點", "維修項目", "損壞情況"],
               [[r["no"], r["location"], r["item"], r["detail"]] for r in stats["unclassified"]],
               widths=[1.6, 4.0, 4.6, 5.8], font_size=9)
    else:
        _para(doc, "本期所有紀錄均成功分類。", size=10)
    if stats["invalid_records"]:
        _para(doc, "無效或測試紀錄", size=10.5, bold=True, space_before=6, space_after=4)
        _table(doc, ["編號", "維修地點", "維修項目", "損壞情況"],
               [[r["no"], r["location"], r["item"], r["detail"]] for r in stats["invalid_records"]],
               widths=[1.6, 4.0, 4.6, 5.8], font_size=9)

    doc.save(path)
    return path
