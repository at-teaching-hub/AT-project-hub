# -*- coding: utf-8 -*-
"""讀取維修申請表（xlsx / xls / csv），回傳原始紀錄。"""
import csv
import io
import os
import warnings

from textutil import norm, squeeze


def _match_column(header, candidates):
    """回傳 2 = 完全相同、1 = 包含、0 = 不匹配。"""
    head = norm(header)
    if not head:
        return 0
    for cand in candidates:
        key = norm(cand)
        if key and head == key:
            return 2
    for cand in candidates:
        key = norm(cand)
        if key and key in head:
            return 1
    return 0


def _read_excel(path, settings, ext):
    import pandas as pd

    engine = "xlrd" if ext == ".xls" else "openpyxl"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=object, engine=engine)
    except Exception as exc:  # noqa: BLE001 - 轉為中文提示
        raise RuntimeError("無法讀取 Excel 檔案：%s（%s）" % (path, exc))
    source = settings.get("source", {})
    wanted = [source.get("sheet_name")] + list(source.get("sheet_candidates") or [])
    wanted = [w for w in wanted if w]
    chosen = None
    for name in sheets:
        if any(norm(name) == norm(w) for w in wanted):
            chosen = name
            break
    if chosen is None:
        for name in sheets:
            if any(norm(w) in norm(name) for w in wanted):
                chosen = name
                break
    if chosen is None:
        for name in sheets:
            if _header_score(sheets[name].values.tolist(), settings) > 0:
                chosen = name
                break
    if chosen is None:
        chosen = list(sheets)[0]
    rows = [list(r) for r in sheets[chosen].values.tolist()]
    return {"name": chosen, "rows": rows, "sheet_names": list(sheets)}


def _read_csv(path, settings):
    encodings = list(settings.get("source", {}).get("csv_encodings") or ["utf-8-sig"])
    encodings.append("utf-8")
    text = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, newline="") as handle:
                text = handle.read()
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if text is None:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    rows = [list(r) for r in csv.reader(io.StringIO(text))]
    return {"name": os.path.basename(path), "rows": rows, "sheet_names": [os.path.basename(path)]}


def _header_score(rows, settings):
    cmap = settings.get("source", {}).get("column_map", {})
    best = 0
    for row in rows[:10]:
        score = 0
        for _field, candidates in cmap.items():
            if any(_match_column(cell, candidates) for cell in row):
                score += 1
        best = max(best, score)
    return best


def read_source(path, settings):
    """回傳 (records, meta)。records 為 list[dict]，key 為內部欄位名。"""
    if not os.path.exists(path):
        raise RuntimeError("找不到檔案：%s" % path)
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm", ".xltx", ".xls"):
        table = _read_excel(path, settings, ext)
    elif ext in (".csv", ".txt", ".tsv"):
        table = _read_csv(path, settings)
    else:
        raise RuntimeError("不支援的檔案格式：%s（請使用 .xlsx / .xls / .csv）" % ext)

    rows = table["rows"]
    cmap = settings.get("source", {}).get("column_map", {})
    best_idx, best_score = 0, -1
    for idx, row in enumerate(rows[:10]):
        score = 0
        for _field, candidates in cmap.items():
            if any(_match_column(cell, candidates) for cell in row):
                score += 1
        if score > best_score:
            best_score, best_idx = score, idx
    header = rows[best_idx] if rows else []
    index = {}
    for field, candidates in cmap.items():
        exact, loose = None, None
        for col, cell in enumerate(header):
            matched = _match_column(cell, candidates)
            if matched == 2:
                exact = col
                break
            if matched == 1 and loose is None:
                loose = col
        target = exact if exact is not None else loose
        if target is not None:
            index[field] = target

    records = []
    for offset, row in enumerate(rows[best_idx + 1:]):
        record = {"_row_no": best_idx + 2 + offset}
        for field, col in index.items():
            record[field] = row[col] if col < len(row) else None
        records.append(record)
    meta = {
        "file": os.path.abspath(path),
        "sheet": table["name"],
        "sheet_names": table["sheet_names"],
        "header_row": best_idx + 1,
        "matched_columns": len(index),
        "raw_rows": len(rows) - best_idx - 1,
        "columns": sorted(index.keys()),
    }
    return records, meta
