# -*- coding: utf-8 -*-
"""統計分析：把清洗後的紀錄整理成報告所需的各項統計表。"""
from datetime import date, timedelta

from textutil import pct, squeeze


def month_range(start, end):
    """回傳期間內所有 'YYYY-MM'（含起訖月）。"""
    months = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append("%04d-%02d" % (year, month))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return months


def in_range(value, start, end):
    return value is not None and start <= value <= end


def average(values):
    values = [v for v in values if v is not None]
    if not values:
        return 0.0
    return round(sum(values) * 1.0 / len(values), 1)


def median(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return 0.0
    mid = len(values) // 2
    if len(values) % 2:
        return float(values[mid])
    return round((values[mid - 1] + values[mid]) / 2.0, 1)


def room_key(record):
    return record.get("room_code") or record.get("room_name") or ""


def room_label(record):
    key = room_key(record)
    if key:
        name = record.get("room_name") or ""
        if name and name != key:
            return "%s（%s）" % (key.upper(), name)
        return key.upper()
    return "未標明地點"


def count_table(records, keyfunc, limit=None, min_count=1):
    """回傳統計表：[{"key":..., "count":...}, ...] 由多到少。"""
    buckets = {}
    for record in records:
        key = keyfunc(record)
        if not key:
            continue
        buckets.setdefault(key, []).append(record)
    rows = [{"key": k, "count": len(v), "records": v} for k, v in buckets.items()]
    rows = [r for r in rows if r["count"] >= min_count]
    rows.sort(key=lambda r: (-r["count"], str(r["key"])))
    return rows[:limit] if limit else rows


def _basic_block(records):
    total = len(records)
    done = [r for r in records if r["is_done"]]
    days = [r["days"] for r in records if r["days"] is not None]
    return {
        "total": total,
        "done": len(done),
        "open": total - len(done),
        "overdue": len([r for r in records if r["is_overdue"]]),
        "completion_rate": pct(len(done), total),
        "avg_days": average(days),
        "median_days": median(days),
        "discipline": len([r for r in records if r["discipline"]]),
    }


def _category_rows(records, prev_records, total):
    prev_counts = {}
    for record in prev_records:
        prev_counts[record["category"]] = prev_counts.get(record["category"], 0) + 1
    by_cat = {}
    for record in records:
        by_cat.setdefault(record["category"], []).append(record)
    rows = []
    for cat, group in by_cat.items():
        done = [r for r in group if r["is_done"]]
        days = [r["days"] for r in group if r["days"] is not None]
        prev = prev_counts.get(cat, 0)
        rows.append({
            "cat": cat,
            "name": group[0]["category_name"],
            "count": len(group),
            "share": pct(len(group), total),
            "done": len(done),
            "rate": pct(len(done), len(group)),
            "avg_days": average(days),
            "prev": prev,
            "delta": len(group) - prev,
        })
    rows.sort(key=lambda r: (-r["count"], r["name"]))
    return rows


def _sub_rows(records, limit):
    by_sub = {}
    for record in records:
        if record["cat"] == "OTHER":
            continue
        by_sub.setdefault((record["category_name"], record["sub"]), []).append(record)
    rows = []
    for (cat_name, sub), group in by_sub.items():
        done = [r for r in group if r["is_done"]]
        rows.append({
            "name": "%s › %s" % (cat_name, sub),
            "count": len(group),
            "done": len(done),
            "rate": pct(len(done), len(group)),
        })
    rows.sort(key=lambda r: -r["count"])
    return rows[:limit] if limit else rows


def _month_rows(records, all_records, months):
    apply_counts = {}
    for record in records:
        apply_counts[record["apply_month"]] = apply_counts.get(record["apply_month"], 0) + 1
    rows = []
    for month in months:
        done = len([r for r in all_records if r["done_month"] == month])
        rows.append({"month": month, "apply": apply_counts.get(month, 0), "done": done})
    return rows


def _floor_category_rows(records, min_count=1):
    buckets = {}
    for record in records:
        floor = record["floor"] or "未標明"
        buckets.setdefault((floor, record["category_name"]), []).append(record)
    rows = []
    for (floor, cat_name), group in buckets.items():
        if len(group) < min_count:
            continue
        rooms = []
        for record in group:
            label = room_label(record)
            if label not in rooms:
                rooms.append(label)
        rows.append({
            "floor": floor,
            "category": cat_name,
            "count": len(group),
            "rooms": rooms,
            "nos": [r["no"] for r in group],
        })
    rows.sort(key=lambda r: (-r["count"], r["floor"]))
    return rows


def _risk_rows(records, risk_keywords):
    rows = []
    for label, keywords in (risk_keywords or {}).items():
        hits = []
        for record in records:
            haystack = (record["raw_item"] or "") + " " + (record["raw_detail"] or "")
            if any(kw in haystack for kw in keywords):
                hits.append(record)
        if hits:
            rows.append({"key": label, "count": len(hits), "records": hits})
    rows.sort(key=lambda r: -r["count"])
    return rows


def summarize(all_records, period_records, start, end, thresholds, prev_records=None, prev_label=""):
    """產生整份報告所需的統計數據。"""
    top_n = int(thresholds.get("top_n", 10))
    prev_records = [r for r in (prev_records or []) if not r["is_invalid"]]
    invalid_records = [r for r in period_records if r["is_invalid"]]
    period_records = [r for r in period_records if not r["is_invalid"]]
    total = len(period_records)
    months = month_range(start, end)
    done_in_period = [r for r in all_records if in_range(r["done_date"], start, end)]

    kpi = _basic_block(period_records)
    kpi["period_start"] = start
    kpi["period_end"] = end
    kpi["months"] = len(months)
    kpi["done_in_period"] = len(done_in_period)
    kpi["prev_total"] = len(prev_records)
    kpi["prev_label"] = prev_label
    kpi["delta_total"] = total - len(prev_records)
    kpi["delta_rate"] = pct(total - len(prev_records), len(prev_records)) if prev_records else 0.0
    kpi["busiest_month"] = ""
    month_rows = _month_rows(period_records, all_records, months)
    if month_rows:
        busiest = max(month_rows, key=lambda r: r["apply"])
        if busiest["apply"]:
            kpi["busiest_month"] = busiest["month"]

    rooms = count_table(period_records, room_key)
    room_rows = []
    for row in rooms[:top_n]:
        group = row["records"]
        cats = {}
        for record in group:
            cats[record["category_name"]] = cats.get(record["category_name"], 0) + 1
        main_cat = sorted(cats.items(), key=lambda kv: -kv[1])[0][0] if cats else ""
        room_rows.append({
            "label": room_label(group[0]),
            "count": row["count"],
            "main_category": main_cat,
            "open": len([r for r in group if not r["is_done"]]),
            "nos": [r["no"] for r in group],
        })

    repeat_min = int(thresholds.get("repeat_cases_min", 2))
    pairs = {}
    for record in period_records:
        key = room_key(record)
        if not key:
            continue
        pairs.setdefault((key, record["category_name"]), []).append(record)
    repeats = []
    for (key, cat_name), group in pairs.items():
        if len(group) >= repeat_min:
            repeats.append({
                "room": room_label(group[0]),
                "room_key": key,
                "category": cat_name,
                "count": len(group),
                "nos": [r["no"] for r in group],
                "items": sorted(set(r["raw_item"] for r in group if r["raw_item"]))[:5],
            })
    repeats.sort(key=lambda r: (-r["count"], r["room"]))

    floor_rows = []
    for row in count_table(period_records, lambda r: r["floor"] or "未標明"):
        floor_rows.append({
            "label": row["key"],
            "count": row["count"],
            "share": pct(row["count"], total),
            "open": len([r for r in row["records"] if not r["is_done"]]),
        })

    grade_rows = []
    for row in count_table(period_records, lambda r: r["grade"]):
        grade_rows.append({
            "label": row["key"],
            "count": row["count"],
            "share": pct(row["count"], total),
            "open": len([r for r in row["records"] if not r["is_done"]]),
        })

    gender_rows = []
    for row in count_table(period_records, lambda r: r["gender"]):
        gender_rows.append({
            "label": row["key"],
            "count": row["count"],
            "share": pct(row["count"], total),
        })

    type_rows = []
    for row in count_table(period_records, lambda r: r["room_type"]):
        type_rows.append({
            "label": row["key"],
            "count": row["count"],
            "share": pct(row["count"], total),
            "open": len([r for r in row["records"] if not r["is_done"]]),
        })

    staff_rows = []
    for row in count_table(period_records, lambda r: r["staff"]):
        group = row["records"]
        staff_rows.append({
            "label": row["key"],
            "count": row["count"],
            "done": len([r for r in group if r["is_done"]]),
            "avg_days": average([r["days"] for r in group if r["days"] is not None]),
        })

    open_records = [r for r in period_records if not r["is_done"]]
    slow = sorted([r for r in period_records if r["days"] is not None], key=lambda r: -r["days"])

    return {
        "kpi": kpi,
        "categories": _category_rows(period_records, prev_records, total),
        "subs": _sub_rows(period_records, top_n * 2),
        "months": month_rows,
        "rooms": room_rows,
        "repeats": repeats,
        "floors": floor_rows,
        "grades": grade_rows,
        "genders": gender_rows,
        "types": type_rows,
        "staff": staff_rows,
        "floor_category": _floor_category_rows(period_records),
        "risks": _risk_rows(period_records, thresholds.get("risk_keywords") or {}),
        "open_records": open_records,
        "slow_records": slow[:top_n],
        "unclassified": [r for r in period_records if r["cat"] == "OTHER"],
        "invalid_records": invalid_records,
        "done_in_period": done_in_period,
        "detail_records": period_records,
    }
