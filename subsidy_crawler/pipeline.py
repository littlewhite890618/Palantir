# -*- coding: utf-8 -*-
"""
subsidy_crawler/pipeline.py — 一鍵跑完整條管線：爬蟲 → 萃取 → 去重 → 新案寫入待審表。

用法：
    python -m subsidy_crawler.pipeline
    python -m subsidy_crawler.pipeline --keep-cache
    python -m subsidy_crawler.pipeline --skip-db
    python -m subsidy_crawler.pipeline --skip-fulltext-dedup

前三階段依序直接呼叫既有函式（不 shell 出去跑各自的 CLI），中間路徑自動以
上一階段實際輸出的 .jsonl 接續，不需人工指定檔名。第四階段把去重後的成功列
跟資料庫比對，只把新案寫進待審表 subsidies_pending（見 common/db.py；--skip-db 可跳過）；
正式表 subsidies 不會被管線改動，要經審核通過才寫入。

每次執行都會寫 data/run_summary.json，出事追加 data/alerts.log（見 common/monitor.py）。
排程由 Windows 工作排程器呼叫 repo 根目錄的 run_pipeline.bat（設定步驟見 md/DEV_WORKFLOW.md）。
"""
import sys
import io
import argparse

# 環境坑：Windows console 是 cp950，直接 print 中文會 UnicodeEncodeError。包成 utf-8。
# 用 encoding 判斷是否已包過：本檔會 import run/extract_fields，兩者也各自做這件事，
# 無條件重包會導致前一層 TextIOWrapper 被回收時關掉底層 buffer，
# 後續 print 噴 ValueError: I/O operation on closed file。
if hasattr(sys.stdout, "buffer") and (sys.stdout.encoding or "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer") and (sys.stderr.encoding or "").lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from . import run as crawl
from . import extract_fields
from . import postprocess
from .common import store, db, monitor


def run_pipeline(keep_cache=False, skip_db=False, skip_fulltext_dedup=False):
    """依序執行爬蟲 → 萃取 → 去重 →（預設）增量同步進待審表，回傳去重階段最終覆蓋寫回的 CSV 路徑。
    skip_db=True 時跳過資料庫步驟，其餘三階段照常執行、檔案照常產生。
    skip_fulltext_dedup=True 時跳過萃取前的全文比對去重（較耗時，除錯/測試用）。
    不論成功失敗都寫 data/run_summary.json；失敗或萃取失敗比例過高時追加 data/alerts.log
    （見 common/monitor.py）。失敗時例外照常往外拋，讓 run_pipeline.bat 拿到非 0 exit code。"""
    started = monitor._now()
    summary = {
        "started_at": started, "finished_at": None, "elapsed_sec": None,
        "result": None, "failed_stage": None, "error": None, "skip_db": skip_db,
        "crawled": None, "extract_success": None, "extract_failed": None, "extract_fail_ratio": None,
        "db_new": None, "db_skipped_known": None, "db_suspected_dup": None,
    }
    stage = None
    try:
        stage = "爬蟲"
        print("=== 階段 1/3：爬蟲 ===")
        crawl.run_all(download=True, keep_cache=keep_cache)
        notices_jsonl = extract_fields.jsonl_path(store.DEFAULT_CSV)
        summary["crawled"] = monitor.count_jsonl(notices_jsonl)

        stage = "萃取"
        print("\n=== 階段 2/3：萃取 ===")
        extract_fields.run(notices_jsonl, extract_fields.DEFAULT_OUT, keep_cache=keep_cache,
                            skip_fulltext_dedup=skip_fulltext_dedup)
        fields_jsonl = extract_fields.jsonl_path(extract_fields.DEFAULT_OUT)

        stage = "去重"
        print("\n=== 階段 3/3：去重 ===")
        postprocess.run(fields_jsonl, extract_fields.DEFAULT_OUT)
        ok, failed = monitor.extract_counts(extract_fields.DEFAULT_OUT)
        summary["extract_success"], summary["extract_failed"] = ok, failed
        summary["extract_fail_ratio"] = monitor.check_extract_fail_ratio(ok, failed)

        if not skip_db:
            stage = "資料庫"
            print("\n=== 階段 4/4：新案寫入待審表 ===")
            stats = db.sync_new_to_pending(extract_fields.DEFAULT_OUT, run_at=started)
            summary["db_new"] = stats["new"]
            summary["db_skipped_known"] = stats["skipped_known"]
            summary["db_suspected_dup"] = stats["suspected_dup"]

        summary["result"] = "成功"
        print("\n=== 管線完成 ===")
        return extract_fields.DEFAULT_OUT
    except BaseException as e:
        summary["result"] = "失敗"
        summary["failed_stage"] = stage
        summary["error"] = f"{type(e).__name__}: {e}"
        monitor.append_alert(monitor.ALERT_PIPELINE_FAILED, f"階段「{stage}」失敗：{summary['error']}")
        raise
    finally:
        finished = monitor._now()
        summary["finished_at"] = finished
        summary["elapsed_sec"] = int((finished - started).total_seconds())
        monitor.write_summary(summary)
        print(f"  執行摘要：{monitor.SUMMARY_PATH}")


def main():
    ap = argparse.ArgumentParser(description="政府補助案爬蟲：一鍵跑完整條管線（爬蟲→萃取→去重→新案寫入待審表）")
    ap.add_argument("--keep-cache", action="store_true",
                    help="爬蟲與萃取兩階段皆保留 pdf_cache 原始檔（預設成功即刪除）")
    ap.add_argument("--skip-db", action="store_true",
                    help="跳過資料庫步驟（預設會把新案寫入待審表 subsidies_pending；測試時不想動資料庫可加此旗標）")
    ap.add_argument("--skip-fulltext-dedup", action="store_true",
                    help="跳過萃取前的全文比對去重（預設會跑，較耗時；除錯/測試時可加此旗標跳過）")
    a = ap.parse_args()
    run_pipeline(keep_cache=a.keep_cache, skip_db=a.skip_db,
                 skip_fulltext_dedup=a.skip_fulltext_dedup)


if __name__ == "__main__":
    main()
