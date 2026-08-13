# -*- coding: utf-8 -*-
"""
common/store.py — 把抓到的須知記錄到 CSV（獨立存放）。

- 一列 = 一份須知檔。
- 用「連結」當 key 去重：同一份再抓只覆蓋該列，不會重複新增。
- 欄位刻意對齊萃取引擎的輸入（部門 / 檔案名稱 / 連結），P3 可直接接。
- 檔案：subsidy_crawler/data/notices.csv（utf-8-sig，Excel 打得開）。
"""
import os
import csv
from datetime import datetime

# 本檔在 common/，往上一層是 subsidy_crawler/，再進 data/。
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")
DEFAULT_CSV = os.path.join(DATA_DIR, "notices.csv")

# CSV 欄位（固定順序）。前三欄＝萃取引擎的輸入格式。
FIELDS = ["部門", "檔案名稱", "連結", "抓取時間"]


def _read_existing(path):
    """讀出既有 CSV，回傳 {連結: 整列dict}。檔案不存在則回空 dict。"""
    rows = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                rows[row["連結"]] = row
    return rows


def save(department, notices, path=DEFAULT_CSV):
    """把 notices=[(檔名, 連結), ...] 寫進 CSV。以「連結」去重（已存在則覆蓋該列）。
    回傳 (新增數, 更新數)。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    rows = _read_existing(path)                       # 先載入既有的（為了去重）
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    added = updated = 0
    for name, url in notices:
        row = {"部門": department, "檔案名稱": name, "連結": url, "抓取時間": now}
        if url in rows:
            updated += 1
        else:
            added += 1
        rows[url] = row                               # 有就覆蓋、沒有就新增 ← 去重關鍵
    # 資料量小，整份重寫最單純。
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for row in rows.values():
            w.writerow(row)
    return added, updated
