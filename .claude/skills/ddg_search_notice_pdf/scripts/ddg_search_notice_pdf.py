# -*- coding: utf-8 -*-
"""
用 DuckDuckGo 搜尋每個（機關, 計畫名稱）pair 的申請須知 PDF。
用法：
  python google_search.py --batch 1 --total 4   # 第1批，共4批
  python google_search.py --test                 # 只跑前3列測試
結果增量寫入 data/search_hits.csv
"""
import sys, io, os, time, argparse, csv
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
def _d(n): return os.path.join(_DATA, n)

HITS_FILE = _d('search_hits.csv')
HITS_COLS = ['機關名稱', '計畫名稱', 'PDF網址', '搜尋query']
DELAY = 1.0

def is_pdf_url(url):
    u = url.lower()
    return u.endswith('.pdf') or 'drive.google.com/file/d/' in u

def ddgs_pdf(機關, 計畫名):
    q1 = f'{計畫名} 申請須知'
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(q1, max_results=5))
        hits = [r['href'] for r in results if is_pdf_url(r.get('href', ''))]
    except Exception:
        hits = []
    time.sleep(DELAY)
    return hits, q1

def append_hits(rows):
    exists = os.path.exists(HITS_FILE)
    with open(HITS_FILE, 'a', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=HITS_COLS)
        if not exists:
            w.writeheader()
        w.writerows(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', type=int, default=1)
    ap.add_argument('--total', type=int, default=4)
    ap.add_argument('--test', action='store_true')
    args = ap.parse_args()

    df = pd.read_csv(_d('否_有計畫名稱.csv'), encoding='utf-8-sig')

    if args.test:
        rows_to_run = df.head(3)
        print('[測試模式] 只跑前3列')
    else:
        n = len(df)
        size = (n + args.total - 1) // args.total
        start = (args.batch - 1) * size
        end = min(start + size, n)
        rows_to_run = df.iloc[start:end]
        print(f'批次 {args.batch}/{args.total}，列 {start+1}–{end}（共{len(rows_to_run)}列）')

    total_pairs = sum(
        len([x for x in str(r['計畫名稱']).split(' | ') if x.strip()])
        for _, r in rows_to_run.iterrows()
    )
    print(f'共 {total_pairs} 個pair，預估 {total_pairs*DELAY*2/60:.0f}–{total_pairs*DELAY*2.5/60:.0f} 分鐘\n')

    found_total = 0
    for idx, (_, row) in enumerate(rows_to_run.iterrows()):
        機關 = str(row['機關名稱'])
        names = [x.strip() for x in str(row['計畫名稱']).split(' | ') if x.strip()]
        for 計畫名 in names:
            pdf_urls, query = ddgs_pdf(機關, 計畫名)
            if pdf_urls:
                new_rows = [{'機關名稱': 機關, '計畫名稱': 計畫名, 'PDF網址': u, '搜尋query': query}
                            for u in pdf_urls]
                append_hits(new_rows)
                found_total += len(new_rows)
                print(f'  ✓ [{機關}] {計畫名[:30]} → {len(pdf_urls)}個PDF')
            else:
                print(f'  - [{機關}] {計畫名[:30]}')
        print(f'  列{idx+1}/{len(rows_to_run)} 完成')

    print(f'\n完成。本批找到 {found_total} 個PDF URL，已寫入 search_hits.csv')

if __name__ == '__main__':
    main()
