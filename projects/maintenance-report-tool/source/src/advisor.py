# -*- coding: utf-8 -*-
"""建議引擎：依統計結果與門檻值，產生可追溯的建議清單。"""


def _nos(values, limit=12):
    values = [str(v) for v in values if v not in (None, "")]
    if not values:
        return ""
    if len(values) > limit:
        return "、".join(values[:limit]) + " 等 %d 宗" % len(values)
    return "、".join(values)


def _add(advices, kind, title, body, evidence=""):
    advices.append({"type": kind, "title": title, "body": body, "evidence": evidence})


def build_advices(stats, thresholds, period_label, prev_label=""):
    advices = []
    kpi = stats["kpi"]
    total = kpi["total"]
    limit = int(thresholds.get("advice_max_per_type", 6))
    overdue_days = int(thresholds.get("overdue_days", 30))

    # ---------- 1. 觀察 ----------
    if prev_label and kpi["prev_total"]:
        direction = "增加" if kpi["delta_total"] >= 0 else "減少"
        body = "本期（%s）共 %d 宗維修申請，較上期（%s）%s %d 宗（%+.1f%%）。" % (
            period_label, total, prev_label, direction, abs(kpi["delta_total"]), kpi["delta_rate"])
    else:
        body = "本期（%s）共 %d 宗維修申請。" % (period_label, total)
    _add(advices, "觀察（整體）", "整體申請量", body)

    if stats["categories"]:
        top = stats["categories"][0]
        _add(advices, "觀察（分類）", "主要維修類別",
              "「%s」共 %d 宗，佔整體 %.1f%%，為本期最主要的維修類別；完成率 %.1f%%，平均處理 %.1f 天。" % (
                  top["name"], top["count"], top["share"], top["rate"], top["avg_days"]))
        rising = [row for row in stats["categories"] if row["delta"] > 0 and row["prev"] > 0]
        rising.sort(key=lambda r: -r["delta"])
        if rising:
            row = rising[0]
            _add(advices, "觀察（趨勢）", "較上期明顯增加",
                  "「%s」較上期增加 %d 宗（上期 %d 宗 → 本期 %d 宗），建議留意是否已形成趨勢。" % (
                      row["name"], row["delta"], row["prev"], row["count"]))

    if kpi["busiest_month"]:
        peak = max(row["apply"] for row in stats["months"])
        _add(advices, "觀察（時間）", "最繁忙月份",
              "%s 為本期申請量最高的月份（%d 宗），建議在該月份前預留維修人力及備件。" % (
                  kpi["busiest_month"], peak))

    _add(advices, "觀察（效率）", "完成情況",
          "本期完成 %d 宗，完成率 %.1f%%，平均處理 %.1f 天（中位數 %.1f 天）；期末仍有 %d 宗未完成，其中 %d 宗已超過 %d 天。" % (
              kpi["done"], kpi["completion_rate"], kpi["avg_days"], kpi["median_days"],
              kpi["open"], kpi["overdue"], overdue_days))

    # ---------- 2. 個別跟進 ----------
    follow = [row for row in stats["repeats"]
              if row["count"] >= int(thresholds.get("repeat_cases_min", 2))]
    for row in follow[:limit]:
        _add(advices, "個別跟進", "%s 的「%s」" % (row["room"], row["category"]),
              "同一地點同類問題期內出現 %d 次，建議作個別跟進，檢查是否源自同一根源（例如同一批設備或同一安裝問題）。" % row["count"],
              "個案編號：" + _nos(row["nos"]))

    # ---------- 3. 部份更換 ----------
    partial = [row for row in stats.get("floor_category") or []
               if row["count"] >= int(thresholds.get("partial_replace_min", 3))]
    for row in partial[:limit]:
        _add(advices, "部份更換", "%s 的「%s」" % (row["floor"], row["category"]),
              "同一樓層同類設備期內出現 %d 宗，涉及 %d 個地點，建議安排批次檢修或部份更換，避免逐宗維修造成重複成本。" % (
                  row["count"], len(row["rooms"])),
              "個案編號：" + _nos(row["nos"]))

    # ---------- 4. 全面更換 ----------
    for row in stats["subs"][:limit]:
        if row["count"] >= int(thresholds.get("full_replace_min", 5)):
            _add(advices, "全面更換", row["name"],
                  "同類設備期內累積 %d 宗維修（完成率 %.1f%%），數量已達顯著水平，建議評估全面更換或整體更新，並於下一財政年度預留預算。" % (
                      row["count"], row["rate"]))

    # ---------- 5. 個別房間建議 ----------
    for row in stats["rooms"][:limit]:
        if row["count"] >= int(thresholds.get("room_alert_min", 3)):
            _add(advices, "個別房間建議", row["label"],
                  "本期間共有 %d 宗申請，主要問題為「%s」，其中 %d 宗仍未完成，建議優先安排實地檢查。" % (
                      row["count"], row["main_category"] or "未分類", row["open"]),
                  "個案編號：" + _nos(row["nos"]))

    # ---------- 6. 個別樓層建議 ----------
    alert_share = float(thresholds.get("floor_share_alert", 0.25)) * 100
    for row in stats["floors"]:
        if row["share"] >= alert_share:
            _add(advices, "個別樓層建議", row["label"],
                  "該樓層佔整體申請 %.1f%%（%d 宗），明顯高於其他樓層，建議為該樓層作重點巡查（電力、門鎖、冷氣及水務）。" % (
                      row["share"], row["count"]))

    # ---------- 7. 男生／女生建議 ----------
    gender_map = {row["label"]: row for row in stats["genders"]}
    boys, girls = gender_map.get("男"), gender_map.get("女")
    if boys or girls:
        parts = []
        if boys:
            parts.append("男生相關地點 %d 宗（%.1f%%）" % (boys["count"], boys["share"]))
        if girls:
            parts.append("女生相關地點 %d 宗（%.1f%%）" % (girls["count"], girls["share"]))
        body = "、".join(parts) + "。"
        wash = [row for row in stats["types"] if row["label"] == "洗手間"]
        if wash:
            body += "當中洗手間／更衣室類地點共 %d 宗。" % wash[0]["count"]
        body += "建議按性別分別檢視洗手間及更衣室的損壞集中情況（水龍頭、廁板、門鎖），並考慮在長假期間統一更新。"
        _add(advices, "男生／女生建議", "男女生相關地點分布", body)

    # ---------- 8. 不同年級建議 ----------
    for row in stats["grades"]:
        if row["count"] >= int(thresholds.get("grade_alert_min", 3)):
            _add(advices, "不同年級建議", row["label"],
                  "該年級課室期內共 %d 宗申請（佔整體 %.1f%%），其中 %d 宗未完成，建議優先檢查該年級課室的枱椅、冷氣及門鎖狀況。" % (
                      row["count"], row["share"], row["open"]))

    # ---------- 9. 其他建議 ----------
    for row in stats["risks"][:3]:
        if row["count"] >= 3:
            _add(advices, "其他建議（風險）", row["key"],
                  "本期共有 %d 宗涉及「%s」的個案，屬需優先處理的類別，建議即時巡查並記錄處理結果。" % (
                      row["count"], row["key"]),
                  "個案編號：" + _nos([r["no"] for r in row["records"]]))

    open_records = stats["open_records"]
    if open_records:
        oldest = sorted(open_records, key=lambda r: (str(r["apply_date"] or r["apply_month"] or ""), r["no"] or 0))
        _add(advices, "其他建議（跟進）", "逾期未完成個案",
              "期末共有 %d 宗未完成個案，最舊的申請日期為 %s，建議逐宗確認進度並更新預計完成日期。" % (
                  len(open_records), oldest[0]["apply_date"]),
              "個案編號：" + _nos([r["no"] for r in oldest]))

    if stats["unclassified"]:
        _add(advices, "其他建議（資料品質）", "待分類項目",
              "有 %d 宗申請未能自動分類，建議確認後把關鍵詞加入分類字典，令下次統計更準確。" % len(stats["unclassified"]),
              "個案編號：" + _nos([r["no"] for r in stats["unclassified"]]))

    if stats["invalid_records"]:
        _add(advices, "其他建議（資料品質）", "無效紀錄",
              "有 %d 宗紀錄屬測試或無內容（例如 test／如圖），建議提醒填寫人補回資料，以免影響統計準確度。" % len(stats["invalid_records"]),
              "個案編號：" + _nos([r["no"] for r in stats["invalid_records"]]))
    return advices
