# -*- coding: utf-8 -*-
"""日期、地點、狀態等欄位清洗與衍生。"""
import re
from datetime import date, datetime, timedelta

from rooms import (
    RoomIndex, class_from_text, floor_from_text, gender_from_text,
    grade_from_class, type_from_text,
)
from textutil import is_blank, norm, squeeze

EXCEL_EPOCH = datetime(1899, 12, 30)
_DATE_FORMATS = [
    "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%Y.%m.%d",
    "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M",
]


def parse_datetime(value):
    """支援 Excel 序號、datetime、各式文字日期，失敗回傳 None。"""
    if value is None or is_blank(value):
        return None
    if hasattr(value, "to_pydatetime"):
        try:
            value = value.to_pydatetime()
        except Exception:  # noqa: BLE001
            pass
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    text = squeeze(value)
    if not text:
        return None
    if re.match(r"^-?\d+(\.\d+)?$", text):
        serial = float(text)
        if serial <= 0 or serial > 80000:
            return None
        return EXCEL_EPOCH + timedelta(days=serial)
    cleaned = text.replace("年", "-").replace("月", "-").replace("日", "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})", cleaned)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year += 2000
        if 1 <= month <= 12 and 1 <= day <= 31:
            try:
                return datetime(year, month, day)
            except ValueError:
                return None
    return None


def parse_date(value):
    dt = parse_datetime(value)
    return dt.date() if dt else None


def parse_item_list(value):
    text = squeeze(value)
    if not text:
        return []
    parts = re.split(r"[,\u3001;/\uff0c\uff1b]+", text)
    return [p.strip() for p in parts if p.strip()]


def parse_discipline(value):
    return "是" in squeeze(value)


def parse_location(text, room_index):
    """由維修地點文字推導房間、樓層、類型、性別、班別、年級。"""
    raw = squeeze(text)
    t = norm(raw)
    codes = []
    if t:
        stripped = t.replace("rm", "")
        for m in re.finditer(r"(n?)(\d{3,6})([a-d])?", stripped):
            prefix, digits, letter = m.group(1), m.group(2), m.group(3) or ""
            if len(digits) == 3:
                for cand in (prefix + digits + letter, prefix + digits):
                    if cand and room_index.lookup(cand):
                        codes.append(cand)
                        break
            else:
                pos = 0
                while pos + 3 <= len(digits):
                    chunk = digits[pos:pos + 3]
                    if room_index.lookup(chunk):
                        codes.append(chunk)
                        pos += 3
                    else:
                        pos += 1
        for m in re.finditer(r"g(\d{2})", stripped):
            cand = "g" + m.group(1)
            if room_index.lookup(cand):
                codes.append(cand)

    first = room_index.lookup(codes[0]) if codes else None
    named = room_index.lookup_by_name(t) if t else None
    floor = floor_from_text(t) or (first or {}).get("floor") or (named or {}).get("floor") or ""
    room_type = type_from_text(t) or (first or {}).get("type") or (named or {}).get("type") or ""
    gender = gender_from_text(t) or (first or {}).get("gender") or (named or {}).get("gender") or ""
    class_code = ""
    for code in codes:
        entry = room_index.lookup(code)
        if entry and entry.get("class_code"):
            class_code = entry["class_code"]
            break
    if not class_code:
        class_code = class_from_text(t)
    grade = grade_from_class(class_code) or (first or {}).get("grade") or (named or {}).get("grade") or ""
    room_name = ""
    if named:
        room_name = named["name"]
    elif first:
        room_name = first["name"]
    return {
        "room_codes": codes,
        "room_code": codes[0] if codes else "",
        "room_name": room_name,
        "floor": floor,
        "room_type": room_type,
        "gender": gender,
        "class_code": class_code,
        "grade": grade,
    }


def build_records(raw_records, settings, room_index, classifier, reference_date=None):
    """清洗＋分類，回傳可用於統計的紀錄清單。"""
    reference = reference_date or date.today()
    overdue_days = int(settings.get("thresholds", {}).get("overdue_days", 30))
    out = []
    skipped = 0
    for raw in raw_records:
        item = squeeze(raw.get("item"))
        detail = squeeze(raw.get("detail"))
        location = squeeze(raw.get("location"))
        apply_dt = parse_datetime(raw.get("apply_date"))
        if not item and not detail and not location and apply_dt is None:
            skipped += 1
            continue
        loc = parse_location(location, room_index)
        result = classifier.classify(item, detail)
        done_date = parse_date(raw.get("done_date")) or parse_date(raw.get("close_date"))
        apply_date = apply_dt.date() if apply_dt else None
        days = (done_date - apply_date).days if (done_date and apply_date) else None
        if days is not None and days < 0:
            days = None
        is_done = done_date is not None
        overdue = False
        if not is_done and apply_date is not None:
            overdue = (reference - apply_date).days > overdue_days
        out.append({
            "no": raw.get("_row_no"),
            "apply_date": apply_date,
            "apply_month": apply_date.strftime("%Y-%m") if apply_date else "",
            "location": location,
            "item": item,
            "detail": detail,
            "staff": squeeze(raw.get("staff")).upper(),
            "discipline": parse_discipline(raw.get("discipline")),
            "done_date": done_date,
            "done_month": done_date.strftime("%Y-%m") if done_date else "",
            "is_done": is_done,
            "days": days,
            "is_overdue": overdue,
            "category": result["cat"],
            "cat": result["cat"],
            "category_name": result["cat_name"],
            "sub": result["sub"],
            "matched_by": result["matched_by"],
            "is_invalid": result["is_invalid"],
            "raw_item": item,
            "raw_detail": detail,
            "room_code": loc["room_code"],
            "room_codes": loc["room_codes"],
            "room_name": loc["room_name"],
            "floor": loc["floor"],
            "room_type": loc["room_type"],
            "gender": loc["gender"],
            "class_code": loc["class_code"],
            "grade": loc["grade"],
        })
    return out, {"skipped_empty_rows": skipped}
