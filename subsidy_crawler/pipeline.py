# -*- coding: utf-8 -*-
"""
subsidy_crawler/pipeline.py — 一鍵跑完整條管線：爬蟲 → 萃取 → 去重 → 寫入資料庫。

用法：
    python -m subsidy_crawler.pipeline
    python -m subsidy_crawler.pipeline --keep-cache
    python -m subsidy_crawler.pipeline --skip-db
    python -m subsidy_crawler.pipeline --skip-fulltext-dedup

前三階段依序直接呼叫既有函式（不 shell 出去跑各自的 CLI），中間路徑自動以
上一階段實際輸出的 .jsonl 接續，不需人工指定檔名。第四階段把去重後的成功列
整批同步進 PostgreSQL 的 subsidies 表（見 common/db.py；--skip-db 可跳過）。

不含排程觸發機制（Task Scheduler / n8n 等）——那是之後的獨立決定；本檔
本身就是「以後被排程呼叫的執行單元」。
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
from .common import store, db


def run_pipeline(keep_cache=False, skip_db=False, skip_fulltext_dedup=False):
    """依序執行爬蟲 → 萃取 → 去重 →（預設）寫入資料庫，回傳去重階段最終覆蓋寫回的 CSV 路徑。
    skip_db=True 時跳過資料庫寫入，其餘三階段照常執行、檔案照常產生。
    skip_fulltext_dedup=True 時跳過萃取前的全文比對去重（較耗時，除錯/測試用）。"""
    print("=== 階段 1/3：爬蟲 ===")
    crawl.run_all(download=True, keep_cache=keep_cache)
    notices_jsonl = extract_fields.jsonl_path(store.DEFAULT_CSV)

    print("\n=== 階段 2/3：萃取 ===")
    extract_fields.run(notices_jsonl, extract_fields.DEFAULT_OUT, keep_cache=keep_cache,
                        skip_fulltext_dedup=skip_fulltext_dedup)
    fields_jsonl = extract_fields.jsonl_path(extract_fields.DEFAULT_OUT)

    print("\n=== 階段 3/3：去重 ===")
    postprocess.run(fields_jsonl, extract_fields.DEFAULT_OUT)

    if not skip_db:
        print("\n=== 階段 4/4：寫入資料庫 ===")
        db.sync_to_db(extract_fields.DEFAULT_OUT)

    print("\n=== 管線完成 ===")
    return extract_fields.DEFAULT_OUT


def main():
    ap = argparse.ArgumentParser(description="政府補助案爬蟲：一鍵跑完整條管線（爬蟲→萃取→去重→寫入資料庫）")
    ap.add_argument("--keep-cache", action="store_true",
                    help="爬蟲與萃取兩階段皆保留 pdf_cache 原始檔（預設成功即刪除）")
    ap.add_argument("--skip-db", action="store_true",
                    help="跳過資料庫寫入（預設會寫入 subsidies 表；測試時不想動正式資料庫可加此旗標）")
    ap.add_argument("--skip-fulltext-dedup", action="store_true",
                    help="跳過萃取前的全文比對去重（預設會跑，較耗時；除錯/測試時可加此旗標跳過）")
    a = ap.parse_args()
    run_pipeline(keep_cache=a.keep_cache, skip_db=a.skip_db,
                 skip_fulltext_dedup=a.skip_fulltext_dedup)


if __name__ == "__main__":
    main()
