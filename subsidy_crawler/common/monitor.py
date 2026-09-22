# -*- coding: utf-8 -*-
"""
subsidy_crawler/common/monitor.py — 管線無人看管執行時留下的「執行摘要」與「告警」。

只寫檔，不寄信、不接 n8n（OpenSpec change pipeline-incremental-review-queue 定案）：
    data/run_summary.json   每次執行都覆蓋寫一份（成功或失敗都寫），看最新一次跑得如何。
    data/alerts.log         出事才追加一行（時間\t類型\t說明），不覆蓋，累積歷次告警。

告警條件：
    - 管線失敗：任何階段拋出例外而中止。
    - 萃取失敗比例過高：失敗列（萃取模型空白）/ 最終總列數 ≥ EXTRACT_FAIL_RATIO_TH。
"""
import os
import csv
import json
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.path.join(HERE, "..", "data"))
SUMMARY_PATH = os.path.join(DATA_DIR, "run_summary.json")
ALERTS_PATH = os.path.join(DATA_DIR, "alerts.log")

EXTRACT_FAIL_RATIO_TH = 0.10   # 最近一次 172 筆失敗 0 筆；偶發 1~2 筆下載失敗不該吵人

ALERT_PIPELINE_FAILED = "管線失敗"
ALERT_EXTRACT_FAIL_RATIO = "萃取失敗比例過高"


def _now():
    return datetime.datetime.now().replace(microsecond=0)


def write_summary(summary, path=SUMMARY_PATH):
    """覆蓋寫出本次執行摘要（datetime 轉 ISO 字串）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2,
                  default=lambda o: o.isoformat() if isinstance(o, datetime.datetime) else str(o))


def append_alert(kind, msg, path=ALERTS_PATH):
    """追加一筆告警（一行一筆，說明裡的換行/tab 壓成空白，方便記事本/Excel 直接開）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    clean = " ".join(str(msg).split())
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{_now().isoformat()}\t{kind}\t{clean}\n")
    print(f"  ⚠ 告警已寫入 {path}：{kind}｜{clean}")


def count_jsonl(path):
    """JSONL 非空行數（爬到的筆數）；檔案不存在回 None。"""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def extract_counts(csv_path):
    """最終結果 CSV 的萃取成功/失敗筆數（失敗＝萃取模型空白，跟 postprocess 判斷一致）。"""
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    failed = sum(1 for r in rows if not (r.get("萃取模型") or "").strip())
    return len(rows) - failed, failed


def check_extract_fail_ratio(success, failed):
    """失敗比例 ≥ 門檻就寫告警；總列數 0 時不算比例（0 筆成功另由資料庫步驟擋下）。
    回傳失敗比例（總列數 0 回 None）。"""
    total = success + failed
    if total == 0:
        return None
    ratio = failed / total
    if ratio >= EXTRACT_FAIL_RATIO_TH:
        append_alert(ALERT_EXTRACT_FAIL_RATIO,
                     f"萃取失敗 {failed}/{total}（{ratio:.0%}，門檻 {EXTRACT_FAIL_RATIO_TH:.0%}）；"
                     f"常見原因：Gemini API 額度用完、來源網站擋下載。")
    return ratio
