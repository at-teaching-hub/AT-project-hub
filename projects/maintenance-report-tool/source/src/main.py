# -*- coding: utf-8 -*-
"""SCR 維修工程統計報告產生器 — 主程式。

用法示例：
  python src/main.py --file "維修表.xlsx" --type 季報 --season 1 --year 2025
  python src/main.py --file "維修表.xlsx" --type 年報 --year 2025
  python src/main.py --file "維修表.xlsx" --type 自訂 --start 2025-09 --end 2026-01
  python src/main.py --file "維修表.xlsx" --list-sheets
"""
import argparse
import calendar
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from textutil import squeeze  # noqa: E402

DEFAULT_FORMATS = "excel,word,pdf"


def _month_start(year, month):
    return date(year, month, 1)


def _month_end(year, month):
    return date(year, month, calendar.monthrange(year, month)[1])


def add_months(value, months):
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def parse_month(text):
    parts = str(text).replace("/", "-").split("-")
    if len(parts) != 2:
        raise ValueError("月份格式應為 YYYY-MM，例如 2025-09（收到：%s）" % text)
    return int(parts[0]), int(parts[1])


def infer_academic_year(records):
    """由資料推斷學年起始年份（9 月制）。"""
    counter = {}
    for record in records:
        month = record.get("apply_month") or ""
        if len(month) < 7:
            continue
        year, number = int(month[:4]), int(month[5:7])
        start_year = year if number >= 9 else year - 1
        counter[start_year] = counter.get(start_year, 0) + 1
    if not counter:
        today = date.today()
        return today.year - 1 if today.month < 9 else today.year
    return max(counter.items(), key=lambda kv: (kv[1], kv[0]))[0]


def resolve_period(args, records):
    report_type = args.type
    if report_type == "自訂" or (args.start and args.end):
        if not (args.start and args.end):
            raise ValueError("自訂報告需要同時提供 --start 與 --end（YYYY-MM）")
        sy, sm = parse_month(args.start)
        ey, em = parse_month(args.end)
        start = _month_start(sy, sm)
        end = _month_end(ey, em)
        if end < start:
            raise ValueError("結束月份不可早於開始月份")
        label = "自訂期間"
    elif report_type == "年報":
        year = args.year or infer_academic_year(records)
        start = date(year, 9, 1)
        end = date(year + 1, 8, 31)
        label = "%d–%d 學年 年報" % (year, (year + 1) % 100)
    else:
        year = args.year or infer_academic_year(records)
        season = args.season or 1
        if season not in (1, 2, 3):
            raise ValueError("--season 只接受 1、2、3")
        if season == 1:
            start, end = date(year, 9, 1), date(year, 12, 31)
            label = "%d–%d 學年 第一季（9–12月）" % (year, (year + 1) % 100)
        elif season == 2:
            start, end = date(year + 1, 1, 1), date(year + 1, 4, 30)
            label = "%d–%d 學年 第二季（1–4月）" % (year, (year + 1) % 100)
        else:
            start, end = date(year + 1, 5, 1), date(year + 1, 8, 31)
            label = "%d–%d 學年 第三季（5–8月）" % (year, (year + 1) % 100)
    months = (end.year - start.year) * 12 + (end.month - start.month) + 1
    prev_end = start - timedelta(days=1)
    prev_start = add_months(start, -months)
    prev_label = "%s 至 %s" % (prev_start.isoformat(), prev_end.isoformat())
    return start, end, label, prev_start, prev_end, prev_label


def build_parser():
    parser = argparse.ArgumentParser(description="SCR 維修工程統計報告產生器")
    parser.add_argument("--file", "-f", required=False, help="維修申請表（.xlsx / .xls / .csv）")
    parser.add_argument("--type", "-t", default="季報", choices=["季報", "年報", "自訂"], help="報告類型（預設季報）")
    parser.add_argument("--season", "-s", type=int, default=None, help="季報季節：1=9–12月、2=1–4月、3=5–8月")
    parser.add_argument("--year", "-y", type=int, default=None, help="學年起始年份，例如 2025 代表 2025–26 學年")
    parser.add_argument("--start", default=None, help="自訂開始月份 YYYY-MM")
    parser.add_argument("--end", default=None, help="自訂結束月份 YYYY-MM")
    parser.add_argument("--formats", default=DEFAULT_FORMATS, help="輸出格式，例如 excel,word,pdf")
    parser.add_argument("--out", default=None, help="輸出資料夾（預設 outputs/）")
    parser.add_argument("--reference-date", default=None, help="計算逾期的基準日期 YYYY-MM-DD（預設今日）")
    parser.add_argument("--no-compare", action="store_true", help="不與上期比較")
    parser.add_argument("--list-sheets", action="store_true", help="只列出工作表名稱")
    parser.add_argument("--interactive", "-i", action="store_true", help="互動模式（逐步輸入）")
    return parser


def ask(prompt, default=None, allow_empty=False):
    suffix = "（預設 %s）" % default if default else ""
    while True:
        value = input("%s%s：" % (prompt, suffix)).strip().strip('"').strip("'")
        if value:
            return value
        if default is not None:
            return default
        if allow_empty:
            return ""
        print("　請輸入內容。")


def interactive_flow():
    print("=" * 60)
    print("  SCR 維修工程統計報告產生器")
    print("=" * 60)
    while True:
        path = ask("請輸入維修表檔案路徑（可直接把檔案拖入本視窗）")
        if os.path.exists(path):
            break
        print("　找不到檔案：%s，請再試一次。" % path)
    print()
    print("請選擇報告類型：")
    print("  1 = 季報　9–12月")
    print("  2 = 季報　1–4月")
    print("  3 = 季報　5–8月")
    print("  4 = 年報　9月–翌年8月")
    print("  5 = 自訂期間")
    while True:
        choice = ask("請輸入 1-5", default="1")
        if choice in ("1", "2", "3", "4", "5"):
            break
        print("　請輸入 1 至 5。")
    argv = ["--file", path]
    if choice == "5":
        start = ask("請輸入開始月份（YYYY-MM，例如 2025-09）")
        end = ask("請輸入結束月份（YYYY-MM，例如 2026-01）")
        argv += ["--type", "自訂", "--start", start, "--end", end]
    elif choice == "4":
        year = ask("請輸入學年起始年份（例如 2025 代表 2025–26 學年）")
        argv += ["--type", "年報", "--year", year]
    else:
        year = ask("請輸入學年起始年份（例如 2025 代表 2025–26 學年）")
        argv += ["--type", "季報", "--season", choice, "--year", year]
    formats = ask("輸出格式（excel,word,pdf，可只填其中幾項）", default="excel,word,pdf")
    argv += ["--formats", formats]
    print()
    return main(argv)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    from config_loader import Config
    config = Config()
    settings = config.settings

    if args.interactive:
        return interactive_flow()

    if not args.file:
        parser.error("需要 --file 指定維修申請表")

    from classifier import Classifier
    from rooms import RoomIndex
    from cleaning import build_records
    from loader import read_source

    if args.list_sheets:
        _records, meta = read_source(args.file, settings)
        print("檔案：%s" % meta["file"])
        print("工作表：" + "、".join(meta["sheet_names"]))
        print("使用的工作表：%s" % meta["sheet"])
        return 0

    raw_records, meta = read_source(args.file, settings)
    room_index = RoomIndex(config.rooms)
    classifier = Classifier(config.classification)
    reference = date.today()
    if args.reference_date:
        reference = date(*[int(x) for x in args.reference_date.split("-")])
    records, clean_meta = build_records(raw_records, settings, room_index, classifier, reference)
    meta["valid_records"] = len(records)
    meta["empty_rows"] = clean_meta["skipped_empty_rows"]

    if not records:
        print("警告：讀不到任何有效紀錄，請確認檔案與欄位。")
        return 1
    if meta["matched_columns"] < 5:
        print("警告：只配對到 %d 個欄位，請確認工作表是否為原始申請表（含標題列）。" % meta["matched_columns"])

    start, end, period_label, prev_start, prev_end, prev_label = resolve_period(args, records)
    if args.no_compare:
        prev_label = ""

    from analyzer import in_range, summarize
    period_records = [r for r in records if in_range(r["apply_date"], start, end)]
    prev_records = [] if args.no_compare else [r for r in records if in_range(r["apply_date"], prev_start, prev_end)]

    thresholds = dict(settings.get("thresholds") or {})
    thresholds["risk_keywords"] = settings.get("risk_keywords") or {}

    stats = summarize(records, period_records, start, end, thresholds,
                      prev_records=prev_records, prev_label=prev_label)

    from advisor import build_advices
    advices = build_advices(stats, thresholds, period_label, prev_label)

    out_dir = args.out or config.out_dir
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    base = "維修工程報告_%s_%s_%s" % (args.type, start.strftime("%Y-%m"), end.strftime("%Y-%m"))
    chart_dir = os.path.join(out_dir, base + "_圖表")

    from charts import build_charts
    chart_paths = build_charts(stats, chart_dir)

    formats = [f.strip().lower() for f in str(args.formats).split(",") if f.strip()]
    outputs = []
    if "excel" in formats or "xlsx" in formats:
        from report_excel import build_excel
        outputs.append(build_excel(stats, advices, meta, config.settings, os.path.join(out_dir, base + ".xlsx"), period_label))
    if "word" in formats or "docx" in formats:
        from report_word import build_word
        outputs.append(build_word(stats, advices, meta, config.settings, os.path.join(out_dir, base + ".docx"), period_label, chart_paths))
    if "pdf" in formats:
        from report_pdf import build_pdf
        outputs.append(build_pdf(stats, advices, meta, config.settings, os.path.join(out_dir, base + ".pdf"), period_label, chart_paths))

    kpi = stats["kpi"]
    print("=" * 62)
    print("報告類型：%s" % period_label)
    print("期間：%s 至 %s" % (start.isoformat(), end.isoformat()))
    print("統計基準：申請日期　資料來源：%s（%s）" % (os.path.basename(meta["file"]), meta["sheet"]))
    print("-" * 62)
    print("申請總數：%d 宗　已完成：%d 宗　完成率：%.1f%%" % (kpi["total"], kpi["done"], kpi["completion_rate"]))
    print("未完成：%d 宗（其中逾期 %d 宗）　平均處理：%.1f 天（中位數 %.1f 天）" % (
        kpi["open"], kpi["overdue"], kpi["avg_days"], kpi["median_days"]))
    if prev_label:
        print("上期（%s）：%d 宗　增減：%+d 宗（%+.1f%%）" % (prev_label, kpi["prev_total"], kpi["delta_total"], kpi["delta_rate"]))
    print("-" * 62)
    print("類別分布：")
    for row in stats["categories"]:
        print("  %-14s %3d 宗　%5.1f%%　完成率 %5.1f%%" % (row["name"], row["count"], row["share"], row["rate"]))
    print("-" * 62)
    print("建議共 %d 項：" % len(advices))
    for advice in advices[:12]:
        print("  【%s】%s — %s" % (advice["type"], advice["title"], advice["body"][:40] + ("…" if len(advice["body"]) > 40 else "")))
    print("=" * 62)
    print("已輸出檔案：")
    for path in outputs:
        print("  " + path)
    print("圖表資料夾：%s" % chart_dir)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        sys.exit(130)
    except Exception as error:  # noqa: BLE001 - 以中文提示取代原始堆疊
        import traceback
        print()
        print("=" * 60)
        print("產生報告時發生錯誤：")
        print("  %s: %s" % (type(error).__name__, error))
        print("-" * 60)
        traceback.print_exc()
        print("=" * 60)
        print("請把以上訊息連同你使用的檔案名稱告知協助者，以便修正。")
        if os.name == "nt":
            input("按 Enter 結束…")
        sys.exit(1)
