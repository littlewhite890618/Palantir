# -*- coding: utf-8 -*-
"""
subsidy_crawler 主入口。

用法：
    python -m subsidy_crawler.run --site kinmen
    python -m subsidy_crawler.run --batch all
    python -m subsidy_crawler.run --batch all --no-download --out new_notices.csv

單站流程：呼叫該站 adapter 的 find_notices() → 逐筆下載到 pdf_cache → 記錄到 CSV。
"""
import sys
import io
import os
import argparse

# 環境坑：Windows console 是 cp950，直接 print 中文會 UnicodeEncodeError。包成 utf-8。
# 用 encoding 判斷是否已包過：pipeline.py 會在同一個行程內 import 多個本來各自獨立執行
# 的模組，若每個都無條件重包一次，前一層 TextIOWrapper 被回收時會連帶關閉底層 buffer，
# 導致後面 print 噴 ValueError: I/O operation on closed file。
if hasattr(sys.stdout, "buffer") and (sys.stdout.encoding or "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer") and (sys.stderr.encoding or "").lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from .common import http, store, render, base
from .sites import (kinmen, tainan, yunlin, hualien, taitung, kaohsiung,
                    nantou, penghu, hsinchu_city, pingtung, yilan, hsinchu_county,
                    lienchiang, ida, sme, keelung, taipei, ndc, doit, digiplus, trade,
                    taoyuan, taichung, miaoli, chiayi_county, chiayi_city, changhua,
                    aoc, cip)

# 原檔快取資料夾（本專案自有，獨立）。
PDF_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "pdf_cache")

# 站名 → adapter 模組。每個 adapter 對外露出 find_notices() 與 DEPARTMENT。
SITES = {
    "kinmen": kinmen,
    "tainan": tainan,
    "yunlin": yunlin,
    "hualien": hualien,
    "taitung": taitung,
    "kaohsiung": kaohsiung,
    "nantou": nantou,
    "penghu": penghu,
    "hsinchu_city": hsinchu_city,
    "pingtung": pingtung,
    "yilan": yilan,
    "hsinchu_county": hsinchu_county,
    "lienchiang": lienchiang,
    "ida": ida,
    "sme": sme,
    "keelung": keelung,
    "taipei": taipei,
    "ndc": ndc,
    "doit": doit,
    "digiplus": digiplus,
    "trade": trade,
    "taoyuan": taoyuan,
    "taichung": taichung,
    "miaoli": miaoli,
    "chiayi_county": chiayi_county,
    "chiayi_city": chiayi_city,
    "changhua": changhua,
    "aoc": aoc,
    "cip": cip,
}

# 載入時就驗證每個 adapter 都符合契約（早點抓錯，不必等執行）
for _site in SITES.values():
    base.check(_site)


def run_site(slug, download=True, csv_path=None, keep_cache=False):
    """跑單一站：找須知 →（可選）下載 → 記錄。
    download=False：只抓清單、不下載檔案（驗證用，快很多）。
    csv_path：指定寫到哪個 CSV（None＝store 的預設 1_crawled_raw.csv）。
    keep_cache=False：下載成功即刪除 pdf_cache 原始檔（已記入清單，快取任務已達成）；
    True 則保留（除錯/人工核對用）。"""
    site = SITES.get(slug)
    if site is None:
        print(f"TODO: {slug} 尚未實作")
        return
    print(f"=== {base.department(site)} ===")
    notices = site.find_notices()
    if not notices:
        print("找不到當年度的申請須知")
        return
    if download:
        use_browser = base.needs_browser_download(site)   # 雲林這種連下載都要瀏覽器
        for name, url in notices:
            if use_browser:
                path = render.selenium_download(url, PDF_CACHE, label=name)
            else:
                path = http.download(url, PDF_CACHE, label=name)
            if path is None:
                print(f"  下載失敗 {name}")
                continue
            print(f"  下載 {name}")
            print(f"       -> {path}")
            if not keep_cache:
                try:
                    os.remove(path)
                except OSError:
                    pass
    added, updated = store.save(base.department(site), notices, path=csv_path or store.DEFAULT_CSV)
    print(f"完成：找到 {len(notices)} 筆（CSV 新增 {added}、更新 {updated}）")


def run_all(download=True, csv_path=None, keep_cache=False):
    """依序跑所有站；單站失敗（連線問題、網站改版）不中斷整批，記下來最後印摘要。"""
    for slug in SITES:
        try:
            run_site(slug, download=download, csv_path=csv_path, keep_cache=keep_cache)
        except Exception as e:
            print(f"  [ERROR] {slug}：{type(e).__name__}: {e}")


def main():
    parser = argparse.ArgumentParser(description="政府補助申請須知抓取系統")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--site", help="只跑單一站（例如 kinmen）")
    group.add_argument("--batch", help="跑一整批（目前支援 all＝全部站）")
    parser.add_argument("--no-download", action="store_true",
                        help="只抓清單、不下載檔案（驗證用，快很多）")
    parser.add_argument("--out", help="指定輸出 CSV 檔名（存在 data/ 底下，例如 new_notices.csv）")
    parser.add_argument("--keep-cache", action="store_true",
                        help="下載成功後保留 pdf_cache 原始檔（預設下載成功即刪除，除錯/人工核對用才需要保留）")
    args = parser.parse_args()

    download = not args.no_download
    csv_path = os.path.join(store.DATA_DIR, args.out) if args.out else None

    if args.site:
        run_site(args.site, download=download, csv_path=csv_path, keep_cache=args.keep_cache)
    elif args.batch:
        if args.batch == "all":
            run_all(download=download, csv_path=csv_path, keep_cache=args.keep_cache)
        else:
            print(f"TODO: 批次 {args.batch} 尚未實作（目前只支援 all）")
    else:
        print("請指定 --site <站名> 或 --batch all")


if __name__ == "__main__":
    main()
