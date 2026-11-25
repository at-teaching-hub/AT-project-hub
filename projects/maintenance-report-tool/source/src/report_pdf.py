# -*- coding: utf-8 -*-
"""輸出 PDF 報告（reportlab）。"""
import os
import struct
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
NAVY = colors.HexColor("#1F3864")
GREY = colors.HexColor("#595959")
LINE = colors.HexColor("#B7C6DA")


def register_fonts():
    """優先使用系統中文 TrueType 字型，否則退回內建 CID 字型。"""
    global FONT, FONT_BOLD
    windows = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
    pairs = [
        (os.path.join(windows, "msjh.ttc"), os.path.join(windows, "msjhbd.ttc"), "MSJH"),
        (os.path.join(windows, "msyh.ttc"), os.path.join(windows, "msyhbd.ttc"), "MSYH"),
        (os.path.join(windows, "mingliu.ttc"), os.path.join(windows, "mingliub.ttc"), "MINGLIU"),
    ]
    for regular, bold, name in pairs:
        if os.path.exists(regular):
            try:
                pdfmetrics.registerFont(TTFont(name, regular, subfontIndex=0))
                if os.path.exists(bold):
                    pdfmetrics.registerFont(TTFont(name + "-Bold", bold, subfontIndex=0))
                    FONT_BOLD = name + "-Bold"
                else:
                    FONT_BOLD = name
                pdfmetrics.registerFontFamily(name, normal=name, bold=FONT_BOLD,
                                              italic=name, boldItalic=FONT_BOLD)
                FONT = name
                return FONT
            except Exception:  # noqa: BLE001
                continue
    for candidate in ("MSung-Light", "STSong-Light"):
        try:
            pdfmetrics.registerFont(UnicodeCIDFont(candidate))
            FONT = candidate
            FONT_BOLD = candidate
            return FONT
        except Exception:  # noqa: BLE001
            continue
    return FONT


def _esc(text):
    """轉義 XML 特殊字元，避免 reportlab 解析錯誤。"""
    return (str("" if text is None else text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def _styles():
    base = ParagraphStyle("cn", fontName=FONT, fontSize=10, leading=14, textColor=colors.black)
    return {
        "title": ParagraphStyle("t", parent=base, fontSize=20, leading=26, alignment=TA_CENTER,
                                textColor=NAVY, spaceAfter=8),
        "subtitle": ParagraphStyle("s", parent=base, fontSize=11, leading=16, alignment=TA_CENTER),
        "small": ParagraphStyle("sm", parent=base, fontSize=9, leading=13, alignment=TA_CENTER,
                                textColor=GREY, spaceAfter=4),
        "heading": ParagraphStyle("h", parent=base, fontSize=13, leading=18, textColor=NAVY,
                                  spaceBefore=12, spaceAfter=6),
        "body": ParagraphStyle("b", parent=base, spaceAfter=4),
        "note": ParagraphStyle("n", parent=base, fontSize=9, leading=13, textColor=GREY, spaceAfter=3),
        "cell": ParagraphStyle("c", parent=base, fontSize=8.5, leading=12),
        "cell_head": ParagraphStyle("ch", parent=base, fontSize=8.5, leading=12,
                                    textColor=colors.white),
    }


def _table(styles, headers, rows, widths, repeat=1):
    data = [[Paragraph(_esc(h), styles["cell_head"]) for h in headers]]
    for values in rows:
        data.append([Paragraph(_esc("" if v is None else v), styles["cell"]) for v in values])
    table = Table(data, colWidths=[w * cm for w in widths], repeatRows=repeat)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E5C8A")),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EAF1F8")]),
    ]))
    return table


def _png_size(path):
    """讀取 PNG 檔頭取得像素尺寸（不需要安裝 Pillow）。"""
    try:
        with open(path, "rb") as handle:
            header = handle.read(24)
        if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        width, height = struct.unpack(">II", header[16:24])
        if width <= 0 or height <= 0:
            return None
        return width, height
    except Exception:  # noqa: BLE001
        return None


def _picture(path, width_cm=16.5, max_height_cm=20.0):
    """建立圖片 flowable，尺寸必須明確指定，否則 reportlab 會誤判為過大。"""
    if not path or not os.path.exists(path):
        return Spacer(1, 1)
    width = width_cm * cm
    size = _png_size(path)
    if not size:
        return Image(path, width=width, height=width * 0.62)
    pixel_width, pixel_height = size
    height = width * pixel_height / pixel_width
    limit = max_height_cm * cm
    if height > limit:
        height = limit
        width = height * pixel_width / pixel_height
    return Image(path, width=width, height=height)


def build_pdf(stats, advices, meta, config, path, period_label, chart_paths):
    register_fonts()
    styles = _styles()
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=2.0 * cm, rightMargin=2.0 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title=config.get("report_title", "維修工程統計報告"))
    story = []
    kpi = stats["kpi"]
    school = config.get("school_name") or ""
    story.append(Paragraph(_esc((school + " " if school else "") + config.get("report_title", "維修工程統計報告")), styles["title"]))
    story.append(Paragraph(_esc("%s　　期間：%s 至 %s" % (period_label, kpi["period_start"], kpi["period_end"])), styles["subtitle"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph("統計基準：申請日期　　產出時間：%s" % datetime.now().strftime("%Y-%m-%d %H:%M"), styles["small"]))
    story.append(Paragraph(_esc("資料來源：%s（工作表：%s）" % (os.path.basename(meta["file"]), meta["sheet"])), styles["small"]))

    story.append(Paragraph("一、摘要", styles["heading"]))
    story.append(_table(styles, ["指標", "數值", "指標", "數值"], [
        ["維修申請總數", "%d 宗" % kpi["total"], "已完成", "%d 宗" % kpi["done"]],
        ["完成率", "%.1f%%" % kpi["completion_rate"], "未完成（期末）", "%d 宗" % kpi["open"]],
        ["逾期未完成", "%d 宗" % kpi["overdue"], "平均處理天數", "%.1f 天" % kpi["avg_days"]],
        ["處理天數中位數", "%.1f 天" % kpi["median_days"], "涉及學生紀律", "%d 宗" % kpi["discipline"]],
        ["與上期比較", "%+d 宗（%+.1f%%）" % (kpi["delta_total"], kpi["delta_rate"]) if kpi["prev_label"] else "—",
         "上期期間", kpi["prev_label"] or "—"],
        ["最繁忙月份", kpi["busiest_month"] or "—", "期內完成宗數", "%d 宗" % kpi["done_in_period"]],
    ], [3.4, 4.0, 3.6, 4.0]))
    story.append(Spacer(1, 6))
    story.append(_picture(chart_paths.get("monthly")))

    story.append(Paragraph("二、維修項目分類統計", styles["heading"]))
    story.append(_table(styles, ["類別", "宗數", "佔比", "已完成", "完成率", "平均處理天數", "上期", "增減"],
                        [[c["name"], c["count"], "%.1f%%" % c["share"], c["done"], "%.1f%%" % c["rate"],
                          "%.1f" % c["avg_days"], c["prev"], "%+d" % c["delta"]] for c in stats["categories"]],
                        [3.4, 1.4, 1.5, 1.5, 1.6, 2.0, 1.4, 1.4]))
    story.append(Spacer(1, 6))
    story.append(_picture(chart_paths.get("category")))
    if stats["subs"]:
        story.append(Paragraph("主要子類（前 10 項）", styles["body"]))
        story.append(_table(styles, ["類別 › 子類", "宗數", "已完成", "完成率"],
                            [[s["name"], s["count"], s["done"], "%.1f%%" % s["rate"]] for s in stats["subs"][:10]],
                            [8.5, 2.0, 2.0, 2.5]))

    story.append(Paragraph("三、趨勢與效率", styles["heading"]))
    story.append(_table(styles, ["月份", "申請宗數", "完成宗數"],
                        [[m["month"], m["apply"], m["done"]] for m in stats["months"]], [4.0, 3.0, 3.0]))
    story.append(Spacer(1, 6))
    story.append(_picture(chart_paths.get("efficiency")))

    story.append(Paragraph("四、地點分析", styles["heading"]))
    story.append(_table(styles, ["樓層", "宗數", "佔比", "未完成"],
                        [[f["label"], f["count"], "%.1f%%" % f["share"], f["open"]] for f in stats["floors"]],
                        [4.5, 2.5, 2.5, 2.5]))
    story.append(Spacer(1, 6))
    story.append(_picture(chart_paths.get("floor")))
    story.append(Paragraph("維修申請最多的地點", styles["body"]))
    story.append(_table(styles, ["地點", "宗數", "主要問題類別", "未完成"],
                        [[r["label"], r["count"], r["main_category"], r["open"]] for r in stats["rooms"]],
                        [6.0, 2.0, 5.5, 2.5]))
    story.append(Spacer(1, 6))
    story.append(_picture(chart_paths.get("room")))
    if stats["repeats"]:
        story.append(Paragraph("同一地點重複出現的同類問題（需個別跟進）", styles["body"]))
        story.append(_table(styles, ["地點", "類別", "次數", "個案編號"],
                            [[r["room"], r["category"], r["count"], "、".join(str(n) for n in r["nos"])]
                             for r in stats["repeats"][:15]], [5.0, 4.5, 1.5, 5.0]))

    story.append(Paragraph("五、性別與年級分析", styles["heading"]))
    story.append(_picture(chart_paths.get("gender_grade")))
    if stats["genders"]:
        story.append(_table(styles, ["性別", "宗數", "佔比"],
                            [[g["label"], g["count"], "%.1f%%" % g["share"]] for g in stats["genders"]],
                            [4.0, 3.0, 3.0]))
    if stats["grades"]:
        story.append(Spacer(1, 4))
        story.append(_table(styles, ["年級", "宗數", "佔比", "未完成"],
                            [[g["label"], g["count"], "%.1f%%" % g["share"], g["open"]] for g in stats["grades"]],
                            [4.0, 3.0, 3.0, 3.0]))

    story.append(PageBreak())
    story.append(Paragraph("六、建議", styles["heading"]))
    story.append(Paragraph("以下建議由系統按既定規則自動產生，每項均附觸發依據或個案編號，方便核實與跟進。", styles["note"]))
    for advice in advices:
        story.append(Paragraph(_esc("【%s】%s" % (advice["type"], advice["title"])),
                               ParagraphStyle("ah", parent=styles["body"], fontName=FONT_BOLD, spaceBefore=6)))
        story.append(Paragraph(_esc(advice["body"]), styles["body"]))
        if advice["evidence"]:
            story.append(Paragraph(_esc(advice["evidence"]), styles["note"]))

    story.append(Paragraph("七、附錄：待分類與無效紀錄", styles["heading"]))
    if stats["unclassified"]:
        story.append(_table(styles, ["編號", "維修地點", "維修項目", "損壞情況"],
                            [[r["no"], r["location"], r["item"], r["detail"]] for r in stats["unclassified"]],
                            [1.6, 4.0, 4.6, 5.8]))
    else:
        story.append(Paragraph("本期所有紀錄均成功分類。", styles["body"]))
    if stats["invalid_records"]:
        story.append(Paragraph("無效或測試紀錄", styles["body"]))
        story.append(_table(styles, ["編號", "維修地點", "維修項目", "損壞情況"],
                            [[r["no"], r["location"], r["item"], r["detail"]] for r in stats["invalid_records"]],
                            [1.6, 4.0, 4.6, 5.8]))

    def _footer(canvas, document):
        canvas.saveState()
        canvas.setFont(FONT, 8)
        canvas.setFillColor(GREY)
        canvas.drawRightString(A4[0] - 2.0 * cm, 1.1 * cm, "第 %d 頁" % document.page)
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return path
