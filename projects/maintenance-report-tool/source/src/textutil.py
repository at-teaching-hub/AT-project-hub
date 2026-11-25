# -*- coding: utf-8 -*-
"""文字正規化與關鍵詞規則比對工具。"""
import re

_FW = {chr(c): chr(c - 0xFEE0) for c in range(0xFF01, 0xFF5F)}


def norm(text):
    """轉小寫、全形轉半形、移除所有空白，用於關鍵詞比對。"""
    if text is None:
        return ""
    s = str(text)
    s = "".join(_FW.get(ch, ch) for ch in s)
    s = re.sub(r"\s+", "", s)
    return s.lower()


def match_rule(text, rule):
    """rule = {"groups": [[kw,...], ...], "none": [kw,...]}
    每個 groups 內的小組至少要命中一個關鍵詞；none 命中任一即整體不匹配。"""
    for kw in (rule.get("none") or []):
        if norm(kw) in text:
            return False
    groups = rule.get("groups") or []
    if not groups:
        return False
    for group in groups:
        if not any(norm(kw) in text for kw in group):
            return False
    return True


def squeeze(text):
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def is_blank(value):
    if value is None:
        return True
    if isinstance(value, float) and value != value:
        return True
    return str(value).strip() in ("", "nan", "NaN", "None")


def to_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def pct(part, whole, digits=1):
    if not whole:
        return 0.0
    return round(part * 100.0 / whole, digits)
