# -*- coding: utf-8 -*-
"""位置（樓層／房間／性別／班別）對照。"""
import re

from textutil import norm

_FLOOR_CN = {"一": "1/F", "二": "2/F", "三": "3/F", "四": "4/F", "五": "5/F", "六": "6/F"}

_ROOM_TYPE_KEYWORDS = [
    ("洗手間", ["洗手間", "廁所", "廁格", "化粧間", "化妝間", "更衣室", "殘廁"]),
    ("課室", ["課室", "班房"]),
    ("教員室", ["教員室", "staffroom", "休息室", "自修室"]),
    ("實驗室", ["實驗室", "lab"]),
    ("行政後勤", ["校務處", "校長室", "副校長室", "醫療室", "茶水間", "辦公室", "工程部", "電機房", "泵房", "小食部", "訓導室", "輔導室", "社工室", "檔案室", "會議室", "更亭"]),
    ("圖書館", ["圖書館"]),
    ("禮堂", ["禮堂", "小禮堂", "hall"]),
    ("戶外設施", ["操場", "籃球場", "羽毛球場", "花園", "天台", "廣場", "溪流", "果園", "蘭苑", "温室"]),
    ("走廊樓梯", ["走廊", "樓梯", "梯間", "大堂", "lobby"]),
    ("貯物室", ["貯物", "儲物室", "潔具室", "storeroom"]),
]


class RoomIndex(object):
    """以 RoomIndex(rooms_json) 建立索引：房間編號、名稱、樓層、班別。"""

    def __init__(self, rooms_payload):
        self.by_code = {}
        self.by_name = []
        for room in (rooms_payload or {}).get("rooms", []):
            code = (room.get("code") or "").strip()
            name = (room.get("name") or "").strip()
            entry = {
                "code": code,
                "floor": room.get("floor") or "",
                "name": name,
                "type": room.get("type") or "",
                "gender": room.get("gender") or "",
                "class_code": (room.get("class_code") or "").upper(),
                "grade": room.get("grade") or "",
            }
            key = code.lower()
            if key and key not in self.by_code:
                self.by_code[key] = entry
            if not code and name:
                self.by_name.append(entry)
        self._codes = sorted(self.by_code.keys(), key=len, reverse=True)

    def lookup(self, code):
        return self.by_code.get(str(code or "").strip().lower())

    def lookup_by_name(self, text_norm):
        for entry in self.by_name:
            key = norm(entry["name"])
            if key and key in text_norm:
                return entry
        return None

    def known_codes(self):
        return self._codes


def floor_from_text(text):
    """由文字判斷樓層，找不到回傳空字串。"""
    t = text or ""
    if re.search(r"(地下|g/f|gf|groundfloor)", t):
        return "地下"
    if re.search(r"(天台|roof)", t):
        return "天台"
    m = re.search(r"([一二三四五六])樓", t)
    if m:
        return _FLOOR_CN[m.group(1)]
    m = re.search(r"([1-6])樓", t)
    if m:
        return m.group(1) + "/F"
    m = re.search(r"([1-6])/f", t)
    if m:
        return m.group(1) + "/F"
    return ""


def type_from_text(text):
    for label, keywords in _ROOM_TYPE_KEYWORDS:
        for kw in keywords:
            if kw in text:
                return label
    return ""


def gender_from_text(text):
    if "男女" in text:
        return "男女"
    if "男" in text:
        return "男"
    if "女" in text:
        return "女"
    return ""


def grade_from_class(class_code):
    if not class_code:
        return ""
    try:
        number = int(class_code[0])
    except (ValueError, IndexError):
        return ""
    return "中" + "一二三四五六"[number - 1] if 1 <= number <= 6 else ""


def class_from_text(text):
    """由地點文字抓出班別，例如「603 （5A)」「2A課室 402室」。"""
    m = re.search(r"\(\s*([1-6])\s*([a-d])\s*\)", text)
    if m:
        return (m.group(1) + m.group(2)).upper()
    m = re.search(r"([1-6])([a-d])(課室|班房|班)", text)
    if m:
        return (m.group(1) + m.group(2)).upper()
    return ""
