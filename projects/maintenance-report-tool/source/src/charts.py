# -*- coding: utf-8 -*-
"""以 matplotlib 產生報告用圖表（PNG）。"""
import os

CHART_FILES = {
    "monthly": "chart_01_monthly_trend.png",
    "category": "chart_02_category.png",
    "floor": "chart_03_floor.png",
    "room": "chart_04_room_top.png",
    "efficiency": "chart_05_efficiency.png",
    "gender_grade": "chart_06_gender_grade.png",
}

_FONT_CANDIDATES = [
    "msjh.ttc", "msjhbd.ttc", "msjhl.ttc", "mingliu.ttc", "kaiu.ttf", "simhei.ttf",
    "msyh.ttc", "msyhbd.ttc", "NotoSansCJK-Regular.ttc", "NotoSansTC-Regular.otf",
]
_FONT_FAMILIES = [
    "Microsoft JhengHei", "Microsoft YaHei", "PMingLiU", "MingLiU", "DFKai-SB",
    "SimHei", "Noto Sans CJK TC", "Noto Sans CJK SC", "Arial Unicode MS",
]
FONT_NAME = ""


def setup_font():
    """挑選可顯示繁體中文的字型；回傳字型名稱。"""
    global FONT_NAME
    if FONT_NAME:
        return FONT_NAME
    import matplotlib
    from matplotlib import font_manager

    directories = [
        os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"),
        os.path.join(os.path.expanduser("~"), "AppData", "Local", "Microsoft", "Windows", "Fonts"),
        "/usr/share/fonts",
        "/System/Library/Fonts",
    ]
    for directory in directories:
        if not os.path.isdir(directory):
            continue
        for name in _FONT_CANDIDATES:
            path = os.path.join(directory, name)
            if os.path.exists(path):
                try:
                    font_manager.fontManager.addfont(path)
                except Exception:  # noqa: BLE001
                    continue
    available = set(f.name for f in font_manager.fontManager.ttflist)
    for family in _FONT_FAMILIES:
        if family in available:
            FONT_NAME = family
            break
    if not FONT_NAME and available:
        FONT_NAME = sorted(available)[0]
    if FONT_NAME:
        matplotlib.rcParams["font.family"] = FONT_NAME
    matplotlib.rcParams["axes.unicode_minus"] = False
    return FONT_NAME


def _finish(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor="white")
    import matplotlib.pyplot as plt
    plt.close(fig)


def _empty_chart(path, message="本期無資料"):
    import matplotlib.pyplot as plt
    setup_font()
    fig = plt.figure(figsize=(7, 3.2))
    fig.text(0.5, 0.5, message, ha="center", va="center", fontsize=13, color="#666666")
    _finish(fig, path)


def build_charts(stats, out_dir):
    """產生所有圖表，回傳 {key: 檔案路徑}。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    setup_font()
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    paths = {}
    for key, filename in CHART_FILES.items():
        paths[key] = os.path.join(out_dir, filename)

    accent = "#2E5C8A"
    accent2 = "#C0504D"

    # 1. 每月申請與完成
    months = stats["months"]
    if months:
        fig, ax = plt.subplots(figsize=(7.2, 3.4))
        labels = [row["month"] for row in months]
        applies = [row["apply"] for row in months]
        dones = [row["done"] for row in months]
        x = range(len(labels))
        ax.bar([i - 0.2 for i in x], applies, width=0.4, label="申請宗數", color=accent)
        ax.bar([i + 0.2 for i in x], dones, width=0.4, label="完成宗數", color="#9BBB59")
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
        ax.set_ylabel("宗數")
        ax.set_title("每月維修申請與完成宗數")
        ax.legend()
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        _finish(fig, paths["monthly"])
    else:
        _empty_chart(paths["monthly"])

    # 2. 維修類別分布
    rows = stats["categories"]
    if rows:
        fig, ax = plt.subplots(figsize=(7.2, max(3.0, 0.42 * len(rows) + 1.2)))
        labels = [row["name"] for row in rows][::-1]
        values = [row["count"] for row in rows][::-1]
        ax.barh(labels, values, color=accent)
        for i, value in enumerate(values):
            ax.text(value + max(values) * 0.01, i, str(value), va="center", fontsize=9)
        ax.set_xlabel("宗數")
        ax.set_title("各類維修項目分布")
        ax.grid(axis="x", linestyle=":", alpha=0.4)
        _finish(fig, paths["category"])
    else:
        _empty_chart(paths["category"])

    # 3. 樓層 × 類別 堆疊圖
    cross = stats.get("floor_category") or []
    floors = [row["label"] for row in stats["floors"]]
    if floors and cross:
        cats = [row["name"] for row in stats["categories"]]
        fig, ax = plt.subplots(figsize=(7.2, 3.6))
        x = range(len(floors))
        lookup = {}
        for row in cross:
            lookup[(row["floor"], row["category"])] = row["count"]
        bottoms = [0] * len(floors)
        palette = ["#2E5C8A", "#C0504D", "#9BBB59", "#8064A2", "#4BACC6", "#F79646",
                   "#7F7F7F", "#C8A46B", "#5E7B9B", "#B07C6B", "#8C9E5E"]
        for index, cat in enumerate(cats):
            values = [lookup.get((floor, cat), 0) for floor in floors]
            if not any(values):
                continue
            ax.bar(x, values, bottom=bottoms, label=cat, color=palette[index % len(palette)])
            bottoms = [b + v for b, v in zip(bottoms, values)]
        ax.set_xticks(list(x))
        ax.set_xticklabels(floors, fontsize=9)
        ax.set_ylabel("宗數")
        ax.set_title("各樓層維修類別分布")
        ax.legend(fontsize=8, ncol=2)
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        _finish(fig, paths["floor"])
    else:
        _empty_chart(paths["floor"])

    # 4. 房間排行
    rooms = stats["rooms"]
    if rooms:
        fig, ax = plt.subplots(figsize=(7.2, max(2.8, 0.42 * len(rooms) + 1.0)))
        labels = [row["label"] for row in rooms][::-1]
        values = [row["count"] for row in rooms][::-1]
        ax.barh(labels, values, color=accent2)
        for i, value in enumerate(values):
            ax.text(value + max(values) * 0.01, i, str(value), va="center", fontsize=9)
        ax.set_xlabel("宗數")
        ax.set_title("維修申請最多的地點（前 %d 位）" % len(rooms))
        ax.grid(axis="x", linestyle=":", alpha=0.4)
        _finish(fig, paths["room"])
    else:
        _empty_chart(paths["room"])

    # 5. 各類別完成率與平均處理天數
    if rows:
        fig, ax = plt.subplots(figsize=(7.2, 3.4))
        labels = [row["name"] for row in rows]
        rates = [row["rate"] for row in rows]
        days = [row["avg_days"] for row in rows]
        x = range(len(labels))
        ax.bar(x, rates, color="#9BBB59", width=0.55)
        ax.set_ylabel("完成率 (%)")
        ax.set_ylim(0, 115)
        for i, rate in enumerate(rates):
            ax.text(i, rate + 2, "%.0f%%" % rate, ha="center", fontsize=8)
        ax2 = ax.twinx()
        ax2.plot(x, days, color=accent2, marker="o", linewidth=1.6, label="平均處理天數")
        ax2.set_ylabel("平均處理天數")
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
        ax.set_title("各類別完成率與平均處理天數")
        ax.grid(axis="y", linestyle=":", alpha=0.4)
        _finish(fig, paths["efficiency"])
    else:
        _empty_chart(paths["efficiency"])

    # 6. 性別與年級
    if stats["genders"] or stats["grades"]:
        fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
        genders = stats["genders"]
        if genders:
            axes[0].bar([row["label"] for row in genders], [row["count"] for row in genders],
                        color=["#4BACC6", "#C0504D", "#8064A2"][:len(genders)])
            axes[0].set_title("男生／女生相關地點", fontsize=10)
            for i, row in enumerate(genders):
                axes[0].text(i, row["count"], str(row["count"]), ha="center", va="bottom", fontsize=9)
        else:
            axes[0].text(0.5, 0.5, "無資料", ha="center", va="center")
        grades = stats["grades"]
        if grades:
            axes[1].bar([row["label"] for row in grades], [row["count"] for row in grades], color=accent)
            axes[1].set_title("各班級／年級申請量", fontsize=10)
            for i, row in enumerate(grades):
                axes[1].text(i, row["count"], str(row["count"]), ha="center", va="bottom", fontsize=9)
        else:
            axes[1].text(0.5, 0.5, "無資料", ha="center", va="center")
        _finish(fig, paths["gender_grade"])
    else:
        _empty_chart(paths["gender_grade"])

    return paths
