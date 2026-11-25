#!/usr/bin/env python3
"""Extract and analyze subject-level STEAM curriculum/activity plans.

Usage:
    python extract_steam_plans.py <source-directory> <work-directory>
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

import openpyxl


PANEL_INFO = {
    "BIO": ("BIO", "生物"),
    "CHEM": ("CHEM", "化學"),
    "CHIN": ("CHIN", "中國語文"),
    "CHIST": ("CHIST", "中國歷史"),
    "COMM": ("COMM", "商業（BAFS／IC）"),
    "CS": ("CS", "公民與社會發展"),
    "D&T": ("D&T", "設計與科技"),
    "DT": ("D&T", "設計與科技"),
    "ECON": ("ECON", "經濟"),
    "ENG": ("ENG", "英國語文"),
    "GEOG": ("GEOG", "地理"),
    "HIST": ("HIST", "歷史"),
    "ICT": ("ICT", "電腦"),
    "LE": ("LE", "生命教育"),
    "MATH": ("MATH", "數學"),
    "MUS": ("MUS", "音樂"),
    "PE": ("PE", "體育"),
    "PHY": ("PHY", "物理"),
    "PTH": ("PTH", "普通話"),
    "SCI": ("SCI", "科學"),
    "VA": ("VA", "視覺藝術"),
}

PANEL_PRIORITIES = {
    "設計與科技": "牽頭建立共通設計週期、原型測試及評分尺度。",
    "科學": "深化探究→設計→測試，與 D&T、數學共備真實問題。",
    "化學": "鞏固實驗與 AI 創作，區分共同活動與本科深化。",
    "生物": "以種植／生態建立長期數據與可持續專題。",
    "英國語文": "把閱讀與寫作轉化為 STEAM 傳意、資料素養及 AI 倫理。",
    "音樂": "加入聲學、數碼創作與工程元素，強化跨科連結。",
    "電腦": "由工具課程走向計算思維、數據建模及 AI 倫理。",
    "地理": "以 GIS、實地數據支援空間決策與可持續方案。",
    "數學": "保留建模優勢，與科學／工程科共同設計應用任務。",
    "商業（BAFS／IC）": "用設計思維、數據與說服力連結市場及社會需要。",
    "物理": "現有活動多為共同活動；需新增本科主導的探究／工程專題。",
    "生命教育": "以共融科技與價值判斷深化科技向善。",
    "體育": "把運動數據延伸為感測器、健康分析與方案設計。",
    "視覺藝術": "以設計思維、用戶研究及工程美學連結 STEAM。",
    "公民與社會發展": "把考察升級為數據／政策方案專題，強化工程與數學。",
    "經濟": "把價格模擬升級為數據建模、實驗與政策評估。",
    "中國歷史": "以 AI 史料詮釋、來源核證及媒體素養深化。",
    "歷史": "發展史料數位化／可視化，連結人文與科技向善。",
    "中國語文": "由 STEAM 敘事、科學傳意及 AI 寫作素養切入。",
    "普通話": "由聲音科技、口語傳意及 AI 語音素養切入。",
}

NEGATIVE_MARKS = {"", "0", "X", "x", "-", "–", "—", "/", "／", "NIL", "nil", "否", "沒有", "无"}
TEMPLATE_NOTES = (
    "**可協商",
    "如未有",
    "此軟本",
    "不需要繳交",
    "以科目簡稱",
    "如有疑問",
)


def as_text(value: Any, multiline: bool = False) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    text = str(value).replace("\xa0", " ").replace("\t", " ")
    if multiline:
        lines = [re.sub(r"[ ]+", " ", line).strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
        return "\n".join(line for line in lines if line)
    return re.sub(r"\s+", " ", text).strip()


def is_marked(value: Any) -> bool:
    return as_text(value).strip() not in NEGATIVE_MARKS


def substantive(value: Any) -> bool:
    text = as_text(value, multiline=True)
    if not text:
        return False
    if text in {"`", "N/A", "n/a", "待填", "稍後填寫", "TBC", "-", "—"}:
        return False
    return bool(re.search(r"[\u4e00-\u9fffA-Za-z0-9]", text))


def file_key(filename: str) -> str:
    head = filename.split("_", 1)[0].strip()
    head = re.sub(r"(?i)steam.*$", "", head).strip("_- ")
    return head


def panel_from_file(filename: str) -> tuple[str, str]:
    key = file_key(filename)
    normalized_key = key.upper()
    if normalized_key in PANEL_INFO:
        return PANEL_INFO[normalized_key]
    for lookup, info in PANEL_INFO.items():
        if normalized_key == lookup.upper():
            return info
    return key or "UNKNOWN", key or "未分類"


def panel_from_subject(subject: Any, fallback: tuple[str, str]) -> tuple[str, str]:
    text = as_text(subject)
    if not text:
        return fallback
    for _, (code, panel) in PANEL_INFO.items():
        if text.upper() == code.upper() or panel.rstrip("科") in text:
            return code, panel
    return fallback


def find_header_row(ws) -> int | None:
    for row in range(1, min(ws.max_row, 12) + 1):
        values = [as_text(ws.cell(row=row, column=col).value) for col in range(1, min(ws.max_column, 24) + 1)]
        joined = " ".join(values)
        if "活動主題" in joined and ("舉辦" in joined or "月份" in joined):
            return row
    return None


def layout_for(ws) -> tuple[str, int | None]:
    a1 = as_text(ws.cell(1, 1).value)
    header_row = find_header_row(ws)
    if a1.startswith("科目："):
        return "alternate", header_row
    if a1 == "科目" or (header_row and as_text(ws.cell(header_row, 1).value) == "科目"):
        return "standard", header_row
    return "unknown", header_row


def template_row(subject: str, title: str, purpose: str = "", content: str = "") -> bool:
    joined = " ".join([subject, title, purpose, content])
    if subject.startswith("**") or any(note in joined for note in TEMPLATE_NOTES):
        return True
    if subject.startswith("例：") or subject.startswith("例:"):
        return True
    if title.strip().upper() == "NIL":
        return True
    return False


def is_nil_row(subject: str, month: str, title: str) -> bool:
    if not title or title.strip().upper() != "NIL":
        return False
    if subject.strip().upper() == "NIL":
        return True
    return as_text(month).upper() == "NIL" and as_text(title).upper() == "NIL"


def classify_activity(activity: dict[str, Any]) -> str:
    title = activity["title"]
    purpose = activity["purpose"]
    if re.search(r"steam\s*(week|day)|stesm\s*day", title, re.I):
        return "STEAM主題活動"
    if re.search(r"比賽|競賽", title):
        return "競賽與挑戰"
    if re.search(r"工作坊|證書|考取|認證", title, re.I):
        return "工作坊與認證"
    if re.search(r"設計|製作|創作|模型|雕塑|繪畫|logo|壁報|布藝|改裝|短片|影片|簡報|匯報|種植", title, re.I):
        return "設計與創作"
    if re.search(r"參觀|考察|研習|之旅|戶外|大灣區|珠海|灣仔", title) or re.search(r"參觀|考察", purpose):
        return "參觀與考察"
    return "課堂應用"


def feature_tags(activity: dict[str, Any]) -> dict[str, bool]:
    text = " ".join([activity["title"], activity["purpose"], activity["content"], activity["assessment"]])
    return {
        "hands_on": bool(re.search(r"製作|設計|實驗|編程|程式|控制|測試|種植|繪畫|雕塑|操作|拍攝|剪輯|模型|機械人|arduino|micro:bit|mbot|vr|ar|體適能測試", text, re.I)),
        "digital_ai": bool(re.search(r"\bAI\b|人工智能|編程|程式|arduino|micro:bit|mbot|scratch|vr|ar|gis|數據|app|電腦|電子|數碼|azure|teachable|互動實驗室", text, re.I)),
        "explicit_ai": bool(re.search(r"\bAI\b|人工智能|azure|teachable|生成圖片|生成图像|ai短片|ai設計", text, re.I)),
        "real_world": bool(re.search(r"真實|日常|生活|社會|環境|可持續|問題|解決|考察|珠海|灣仔|大灣區|辦公室|購物|停車|汽水罐|饑荒|輪椅|體適能|文化|藝術館|中草藥|種植|價格|社交媒體", text)),
        "tech_good": bool(re.search(r"倫理|道德|可持續|社會|責任|共融|輪椅|環境|饑荒|媒體|資訊素養|文化|中草藥|健康|體適能", text)),
        "talent": bool(re.search(r"比賽|競賽|證書|考取|人才|認證", text)),
        "product_assessment": bool(re.search(r"作品|習作|報告|工作紙|反思|問卷|分數|評分|證書|測試|成績", activity["assessment"])),
        "observation_assessment": bool(re.search(r"觀察|參與|投入|討論|表演|演唱", activity["assessment"])),
    }


def normalize_title(title: str) -> str:
    text = title.upper().replace("STESM", "STEAM")
    text = text.replace("1天之旅", "一天之旅").replace("1 天之旅", "一天之旅")
    text = re.sub(r"[\s\\/\-_:：,，.。()（）「」『』]", "", text)
    return text


def maturity(metrics: dict[str, Any]) -> str:
    if metrics["activities"] == 0:
        return "未填報"
    if metrics["activities"] >= 5 and metrics["breadth"] >= 4 and metrics["avg_elements"] >= 3:
        return "旗艦"
    if metrics["breadth"] >= 3 or (metrics["activities"] >= 4 and metrics["breadth"] >= 2):
        return "深化"
    return "起步"


def parse_standard(ws, header_row: int, fallback_panel: tuple[str, str], filename: str) -> tuple[list[dict[str, Any]], set[str]]:
    activities: list[dict[str, Any]] = []
    nil_panels: set[str] = set()
    last_subject = ""
    subject_code_raw = ""
    start = header_row + 1
    for row in range(start, ws.max_row + 1):
        subject = as_text(ws.cell(row=row, column=1).value)
        month = as_text(ws.cell(row=row, column=2).value)
        title = as_text(ws.cell(row=row, column=3).value)
        purpose = as_text(ws.cell(row=row, column=4).value, multiline=True)
        content = as_text(ws.cell(row=row, column=5).value, multiline=True)
        if subject and not subject.startswith("例") and not subject.startswith("**"):
            last_subject = subject
        effective_subject = subject or last_subject
        code, panel = panel_from_subject(effective_subject, fallback_panel)
        if is_nil_row(effective_subject, month, title):
            nil_panels.add(panel)
            continue
        if template_row(effective_subject, title, purpose, content):
            continue
        if not title:
            continue
        subject_code_raw = effective_subject or code
        activity = {
            "file": filename,
            "sheet": ws.title,
            "row": row,
            "subject_raw": subject_code_raw,
            "subject_code": code,
            "panel": panel,
            "month": month,
            "title": title,
            "purpose": purpose,
            "content": content,
            "location": as_text(ws.cell(row=row, column=6).value),
            "level": as_text(ws.cell(row=row, column=7).value),
            "teacher": as_text(ws.cell(row=row, column=8).value),
            "assessment": as_text(ws.cell(row=row, column=9).value, multiline=True),
            "S": is_marked(ws.cell(row=row, column=10).value),
            "T": is_marked(ws.cell(row=row, column=11).value),
            "E": is_marked(ws.cell(row=row, column=12).value),
            "A": is_marked(ws.cell(row=row, column=13).value),
            "M": is_marked(ws.cell(row=row, column=14).value),
            "cross": is_marked(ws.cell(row=row, column=15).value),
            "partners": as_text(ws.cell(row=row, column=16).value),
            "review": as_text(ws.cell(row=row, column=17).value, multiline=True),
        }
        activity["element_count"] = sum(bool(activity[k]) for k in "STEAM")
        activity["category"] = classify_activity(activity)
        activity.update(feature_tags(activity))
        activities.append(activity)
    return activities, nil_panels


def parse_alternate(ws, header_row: int, fallback_panel: tuple[str, str], filename: str) -> tuple[list[dict[str, Any]], set[str]]:
    activities: list[dict[str, Any]] = []
    nil_panels: set[str] = set()
    subject_name = as_text(ws.cell(1, 2).value) or fallback_panel[1]
    code, panel = panel_from_subject(subject_name, fallback_panel)
    start = header_row + 1
    if start <= ws.max_row:
        subheaders = [as_text(ws.cell(start, col).value).upper() for col in range(9, 14)]
        if subheaders == ["S", "T", "E", "A", "M"]:
            start += 1
    for row in range(start, ws.max_row + 1):
        month = as_text(ws.cell(row=row, column=1).value)
        title = as_text(ws.cell(row=row, column=2).value)
        purpose = as_text(ws.cell(row=row, column=3).value, multiline=True)
        content = as_text(ws.cell(row=row, column=4).value, multiline=True)
        if is_nil_row(panel, month, title):
            nil_panels.add(panel)
            continue
        if template_row(subject_name, title, purpose, content):
            continue
        if not title:
            continue
        activity = {
            "file": filename,
            "sheet": ws.title,
            "row": row,
            "subject_raw": subject_name,
            "subject_code": code,
            "panel": panel,
            "month": month,
            "title": title,
            "purpose": purpose,
            "content": content,
            "location": as_text(ws.cell(row=row, column=5).value),
            "level": as_text(ws.cell(row=row, column=6).value),
            "teacher": as_text(ws.cell(row=row, column=7).value),
            "assessment": as_text(ws.cell(row=row, column=8).value, multiline=True),
            "S": is_marked(ws.cell(row=row, column=9).value),
            "T": is_marked(ws.cell(row=row, column=10).value),
            "E": is_marked(ws.cell(row=row, column=11).value),
            "A": is_marked(ws.cell(row=row, column=12).value),
            "M": is_marked(ws.cell(row=row, column=13).value),
            "cross": is_marked(ws.cell(row=row, column=14).value),
            "partners": as_text(ws.cell(row=row, column=15).value),
            "review": as_text(ws.cell(row=row, column=16).value, multiline=True),
        }
        activity["element_count"] = sum(bool(activity[k]) for k in "STEAM")
        activity["category"] = classify_activity(activity)
        activity.update(feature_tags(activity))
        activities.append(activity)
    return activities, nil_panels


def build_metrics(activities: list[dict[str, Any]], all_panels: list[tuple[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for code, panel in all_panels:
        subset = [a for a in activities if a["panel"] == panel]
        unique = len({normalize_title(a["title"]) for a in subset})
        element_counts = {key: sum(bool(a[key]) for a in subset) for key in "STEAM"}
        breadth = sum(1 for count in element_counts.values() if count > 0)
        avg_elements = round(sum(a["element_count"] for a in subset) / len(subset), 3) if subset else 0
        row = {
            "panel": panel,
            "code": code,
            "activities": len(subset),
            "unique_themes": unique,
            **element_counts,
            "breadth": breadth,
            "cross_records": sum(1 for a in subset if a["cross"]),
            "hands_on": sum(1 for a in subset if a["hands_on"]),
            "digital_ai": sum(1 for a in subset if a["digital_ai"]),
            "real_world": sum(1 for a in subset if a["real_world"]),
            "tech_good": sum(1 for a in subset if a["tech_good"]),
            "talent": sum(1 for a in subset if a["talent"]),
            "all_five": sum(1 for a in subset if a["element_count"] == 5),
            "avg_elements": avg_elements,
        }
        row["maturity"] = maturity(row)
        row["priority"] = PANEL_PRIORITIES.get(panel, "選擇一個與本科課程直接相關的真實問題專題，先深化一個可評估的 STEAM 單元。")
        rows.append(row)
    rows.sort(key=lambda x: (-x["activities"], -x["breadth"], x["panel"]))
    return rows


def export_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_brief(path: Path, data: dict[str, Any]) -> None:
    k = data["kpis"]
    lines = [
        "# STEAM Review Brief",
        "",
        f"- Source directory: `{data['source_directory']}`",
        f"- Plan files: {k['files']}",
        f"- Active subject panels: {k['active_panels']}",
        f"- NIL panels: {', '.join(k['nil_panels']) if k['nil_panels'] else 'None'}",
        f"- Subject-reported activity records: {k['activity_records']}",
        f"- Deduplicated themes: {k['unique_themes']}",
        f"- Cross-subject records / unique themes: {k['cross_records']} / {k['cross_unique_themes']}",
        f"- Average elements per activity: {k['avg_elements']}/5",
        f"- Activities with all five elements: {k['all_five']} ({k['all_five_pct']:.1f}%)",
        f"- Substantive review entries: {k['substantive_reviews']} ({k['substantive_review_pct']:.1f}%)",
        "",
        "## Element coverage",
        "",
    ]
    for key, count, pct in data["element_counts"]:
        lines.append(f"- {key}: {count} ({pct:.1f}%)")
    lines += ["", "## Feature counts", ""]
    for key, value in data["feature_counts"].items():
        lines.append(f"- {key}: {value}")
    lines += ["", "## Largest duplicated titles", ""]
    if data["duplicate_titles"]:
        for item in data["duplicate_titles"][:10]:
            lines.append(f"- {item['title']}: {item['records']} records; panels: {', '.join(item['panels'])}")
    else:
        lines.append("- None")
    lines += [
        "",
        "## Audit",
        "",
        f"- Parsed worksheets: {data['audit']['parsed_worksheets']}",
        f"- Parse errors: {len(data['audit']['errors'])}",
    ]
    for error in data["audit"]["errors"]:
        lines.append(f"- ERROR: {error}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir")
    parser.add_argument("work_dir")
    args = parser.parse_args()

    source = Path(args.source_dir)
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        raise SystemExit(f"Source directory not found: {source}")

    files = sorted([p for p in source.glob("*.xlsx") if not p.name.startswith("~$")])
    if not files:
        raise SystemExit(f"No .xlsx files found in: {source}")

    activities: list[dict[str, Any]] = []
    nil_panels: set[str] = set()
    parsed_worksheets = 0
    errors: list[str] = []
    all_panel_map: dict[str, tuple[str, str]] = {}
    file_records: list[dict[str, Any]] = []

    for path in files:
        fallback = panel_from_file(path.name)
        all_panel_map[fallback[1]] = fallback
        before = len(activities)
        try:
            workbook = openpyxl.load_workbook(path, data_only=True, read_only=False)
            for ws in workbook.worksheets:
                if ws.max_row <= 1 or ws.max_column <= 1:
                    continue
                layout, header_row = layout_for(ws)
                if layout == "standard" and header_row:
                    parsed, nils = parse_standard(ws, header_row, fallback, path.name)
                elif layout == "alternate" and header_row:
                    parsed, nils = parse_alternate(ws, header_row, fallback, path.name)
                else:
                    continue
                parsed_worksheets += 1
                activities.extend(parsed)
                nil_panels.update(nils)
                if parsed:
                    all_panel_map[parsed[0]["panel"]] = (parsed[0]["subject_code"], parsed[0]["panel"])
            count = len(activities) - before
            file_records.append({
                "file": path.name,
                "panel": fallback[1],
                "records": count,
                "sheets": [ws.title for ws in workbook.worksheets],
            })
        except Exception as exc:  # Keep going so one malformed workbook does not hide the rest.
            errors.append(f"{path.name}: {exc}")
            file_records.append({"file": path.name, "panel": fallback[1], "records": 0, "sheets": []})

    all_panels = list(all_panel_map.values())
    metrics = build_metrics(activities, all_panels)
    unique_map: dict[str, dict[str, Any]] = {}
    for activity in activities:
        key = normalize_title(activity["title"])
        item = unique_map.setdefault(key, {"title": activity["title"], "records": 0, "panels": set(), "cross": False})
        item["records"] += 1
        item["panels"].add(activity["panel"])
        item["cross"] = item["cross"] or activity["cross"]
    unique_values = list(unique_map.values())
    cross_values = [item for item in unique_values if item["cross"]]

    element_counts = [(key, sum(1 for a in activities if a[key]), (sum(1 for a in activities if a[key]) / len(activities) * 100 if activities else 0)) for key in "STEAM"]
    feature_keys = ["hands_on", "digital_ai", "explicit_ai", "real_world", "tech_good", "talent", "product_assessment", "observation_assessment"]
    feature_counts = {key: sum(1 for a in activities if a[key]) for key in feature_keys}
    category_counts = Counter(a["category"] for a in activities)
    all_five = sum(1 for a in activities if a["element_count"] == 5)
    substantive_reviews = sum(1 for a in activities if substantive(a["review"]))
    active_panels = [m for m in metrics if m["activities"] > 0]
    nil_panel_names = [m["panel"] for m in metrics if m["activities"] == 0]

    duplicate_titles = []
    for item in unique_values:
        if item["records"] > 1:
            duplicate_titles.append({
                "title": item["title"],
                "records": item["records"],
                "panels": sorted(item["panels"]),
            })
    duplicate_titles.sort(key=lambda x: (-x["records"], x["title"]))

    data = {
        "schema_version": "1.0",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_directory": str(source.resolve()),
        "audit": {
            "file_count": len(files),
            "parsed_worksheets": parsed_worksheets,
            "errors": errors,
        },
        "kpis": {
            "files": len(files),
            "active_panels": len(active_panels),
            "nil_panels": nil_panel_names,
            "activity_records": len(activities),
            "unique_themes": len(unique_values),
            "cross_records": sum(1 for a in activities if a["cross"]),
            "cross_unique_themes": len(cross_values),
            "avg_elements": round(sum(a["element_count"] for a in activities) / len(activities), 3) if activities else 0,
            "all_five": all_five,
            "all_five_pct": (all_five / len(activities) * 100) if activities else 0,
            "substantive_reviews": substantive_reviews,
            "substantive_review_pct": (substantive_reviews / len(activities) * 100) if activities else 0,
        },
        "metrics": metrics,
        "activities": activities,
        "element_counts": element_counts,
        "feature_counts": feature_counts,
        "category_counts": dict(category_counts),
        "duplicate_titles": duplicate_titles,
        "source_files": file_records,
    }

    (work / "steam_review_data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    export_csv(work / "activities.csv", activities, [
        "file", "sheet", "row", "panel", "subject_raw", "month", "title", "purpose", "content",
        "location", "level", "assessment", "S", "T", "E", "A", "M", "element_count", "cross",
        "partners", "hands_on", "digital_ai", "explicit_ai", "real_world", "tech_good", "talent",
        "review", "category",
    ])
    export_csv(work / "subject_summary.csv", metrics, [
        "panel", "code", "activities", "unique_themes", "S", "T", "E", "A", "M", "breadth",
        "cross_records", "hands_on", "digital_ai", "real_world", "tech_good", "talent",
        "all_five", "avg_elements", "maturity", "priority",
    ])
    write_brief(work / "analysis_brief.md", data)

    print(json.dumps({
        "output": str(work / "steam_review_data.json"),
        "files": len(files),
        "activities": len(activities),
        "unique_themes": len(unique_values),
        "nil_panels": nil_panel_names,
        "errors": errors,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()