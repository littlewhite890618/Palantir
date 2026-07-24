# -*- coding: utf-8 -*-
"""
Fix 2：用 Playwright（真瀏覽器）render 否_無計畫名稱.csv 的頁面（含 403/SPA），
擷取頁面上的補助案計畫名；有抓到 → 移到 否_有計畫名稱.csv。
"""
import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
def _d(n): return os.path.join(_DATA, n)
A, B = _d('否_有計畫名稱.csv'), _d('否_無計畫名稱.csv')

ITEM_KW = ['補助', '獎助', '補貼', '津貼', '獎勵', '計畫', '徵件', '徵選', '申請', '方案', '要點']
NEG = ['支付或接受', '施政計畫', '業務統計', '旅費', '出國', '考察', '利益衝突', '內部控制',
       '資訊公開', '補助公開', '公開專區', '中長程計畫', '統計方案', '執行情形', '聲明書',
       '快速檢測', '線上申請', '進度查詢', '常見問題', '志願服務', '志工', '接受補助',
       '捐贈名單', '名單清冊', '會員', '登入', '網站導覽', '隱私']

def extract_names(html):
    soup = BeautifulSoup(html, 'html.parser')
    out = []
    for a in soup.find_all('a'):
        t = a.get_text(strip=True)
        if 8 <= len(t) <= 45 and any(k in t for k in ITEM_KW) and not any(n in t for n in NEG):
            out.append(t)
    return list(dict.fromkeys(out))

cols = ['機關名稱', 'HTTP狀態', '原網址', '計畫名稱所在網址', '網站類別', '計畫名稱']
a = pd.read_csv(A, encoding='utf-8-sig')
b = pd.read_csv(B, encoding='utf-8-sig')

keep_b, moved = [], []
with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/122.0 Safari/537.36',
        ignore_https_errors=True, locale='zh-TW')
    total = len(b)
    for n, (_, r) in enumerate(b.iterrows(), 1):
        name = str(r['機關名稱']); url = str(r['原網址'])
        rec = {c: r.get(c, '') for c in cols}
        names = []
        if url.startswith('http'):
            page = ctx.new_page()
            try:
                page.goto(url, timeout=30000, wait_until='domcontentloaded')
                try:
                    page.wait_for_load_state('networkidle', timeout=8000)
                except Exception:
                    pass
                time.sleep(1)
                names = extract_names(page.content())
            except Exception as e:
                rec['HTTP狀態'] = f'playwright:{type(e).__name__}'
            finally:
                page.close()
        if names:
            rec['計畫名稱'] = ' | '.join(names[:15])
            rec['計畫名稱所在網址'] = url
            rec['HTTP狀態'] = '200(Playwright)'
            moved.append(rec)
            print(f'[{n}/{total}] ✅{len(names)}個  {name[:22]}')
        else:
            keep_b.append(rec)
            print(f'[{n}/{total}] ❌無  {name[:22]}')
    browser.close()

a_rows = [{c: r.get(c, '') for c in cols} for _, r in a.iterrows()] + moved
pd.DataFrame(a_rows, columns=cols).to_csv(A, index=False, encoding='utf-8-sig')
pd.DataFrame(keep_b, columns=cols).to_csv(B, index=False, encoding='utf-8-sig')
print(f'\nFix2 完成：Playwright 補抓移回 {len(moved)} 筆')
print(f'  有計畫名稱: {len(a_rows)}  /  無計畫名稱: {len(keep_b)}')
