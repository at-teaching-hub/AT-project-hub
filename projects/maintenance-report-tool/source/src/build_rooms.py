# -*- coding: utf-8 -*-
"""由 kys_room.xlsx 重新產生 config/rooms.json。

用法：python src/build_rooms.py --file "kys_room.xlsx"
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_loader import load_json, project_root  # noqa: E402

FLOOR_MAP = {"G/F": "地下", "GF": "地下", "一樓": "1/F", "二樓": "2/F", "三樓": "3/F",
             "四樓": "4/F", "五樓": "5/F", "六樓": "6/F"}
TYPE_KEYWORDS = [
    ("洗手間", ["洗手間", "廁", "化粧間", "化妝間", "更衣室"]),
    ("教員室", ["教員室", "Staff Room", "自修室", "休息室", "Common Room"]),
    ("實驗室", ["實驗室"]),
    ("貯物室", ["貯物", "Store", "潔具室"]),
    ("戶外設施", ["操場", "籃球場", "羽毛球場", "花園", "溪流", "果園", "蘭苑", "温室", "展示閣", "種植室", "魚菜", "智能值物園"]),
    ("行政後勤", ["校務處", "校長室", "副校長室", "醫療室", "茶水間", "工程部", "電機房", "總電掣房", "泵房", "小食部",
                 "訓導室", "輔導室", "社工室", "檔案室", "電話機房", "會議室", "更亭"]),
]


def normalize_floor(text):
    value = str(text or "").strip()
    if re.match(r"^(G/F|GF)$", value, re.IGNORECASE):
        return "地下"
    match = re.match(r"^F([1-6])$", value, re.IGNORECASE)
    if match:
        return match.group(1) + "/F"
    if value in FLOOR_MAP:
        return FLOOR_MAP[value]
    match = re.match(r"^([1-6])樓?$", value)
    if match:
        return match.group(1) + "/F"
    if re.search(r"天台|Roof", value, re.IGNORECASE):
        return "天台"
    return value or "未標明"


def room_type(name, class_code):
    if re.search(r"洗手間|廁|化粧間|化妝間|更衣室", name):
        return "洗手間"
    if class_code:
        return "課室"
    for label, keywords in TYPE_KEYWORDS:
        for keyword in keywords:
            if keyword in name:
                return label
    return "特別室"


def room_gender(name):
    if "男女" in name:
        return "男女"
    if "男" in name:
        return "男"
    if "女" in name:
        return "女"
    return ""


def grade_of(class_code):
    if not class_code:
        return ""
    return "中" + "一二三四五六"[int(class_code[0]) - 1]


def build(path, sheet="Main Building"):
    import pandas as pd

    frame = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)
    rows = frame.values.tolist()
    rooms = []
    for row in rows[2:]:
        if len(row) < 8:
            continue
        loc_code, _loc_barcode, _loc_en, _loc_chi = row[0], row[1], row[2], row[3]
        sub_code, _sub_barcode, _sub_en, sub_chi = row[4], row[5], row[6], row[7]
        name = str(sub_chi or "").strip()
        if not name or name == "nan":
            continue
        code = ""
        match = re.match(r"^(N?\d{3}[A-Da-d]?|G\d{2}|R\d{1,2})", name)
        if match:
            code = match.group(1)
        else:
            match = re.match(r"^(N?\d{3}[A-Da-d]?|G\d{2}|R\d{1,2})$", str(sub_code or "").strip())
            if match:
                code = match.group(1)
        match = re.search(r"[（(]\s*([1-6])\s*([A-Da-d])\s*[)）]", name)
        class_code = (match.group(1) + match.group(2)).upper() if match else ""
        rooms.append({
            "code": code,
            "floor": normalize_floor(loc_code),
            "name": name,
            "type": room_type(name, class_code),
            "gender": room_gender(name),
            "class_code": class_code,
            "grade": grade_of(class_code),
        })
    return rooms


def main(argv=None):
    parser = argparse.ArgumentParser(description="由 kys_room.xlsx 產生 config/rooms.json")
    parser.add_argument("--file", "-f", required=True, help="年級／位置對照表（xlsx）")
    parser.add_argument("--sheet", default="Main Building", help="工作表名稱")
    args = parser.parse_args(argv)
    rooms = build(args.file, args.sheet)
    target = os.path.join(project_root(), "config", "rooms.json")
    payload = load_json(target) if os.path.exists(target) else {}
    payload.update({"version": "1.0", "source_file": os.path.basename(args.file), "rooms": rooms})
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    print("已寫入 %s，共 %d 個位置。" % (target, len(rooms)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
