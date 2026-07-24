# -*- coding: utf-8 -*-
"""
找「補助案列表頁」：判斷 URL 目前是否已是補助案列表頁；
若不是，往下鑽一層找出「點進去直接是補助案列表」的頁面，回傳建議 URL。
輸出 list_page_result.csv
"""
import sys, io, time, argparse, ssl
from urllib.parse import urljoin, urlparse
import requests, urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from bs4 import BeautifulSoup
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
urllib3.disable_warnings()

import os
_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
def _d(name):
    return os.path.join(_DATA, name)

IN_CSV  = _d('政府官方平台資料庫_整理版v5.csv')
OUT_CSV = _d('list_page_result.csv')

H = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
    'Upgrade-Insecure-Requests': '1',
}


class LegacyTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *a, **k):
        ctx = create_urllib3_context()
        ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        k['ssl_context'] = ctx
        return super().init_poolmanager(*a, **k)


SESSION = requests.Session()
SESSION.headers.update(H)
SESSION.mount('https://', LegacyTLSAdapter())

# 補助案項目的關鍵字（判斷「列表項」用）
ITEM_KW = ['補助', '獎助', '補貼', '津貼', '獎勵', '計畫', '徵件', '徵選', '申請', '方案', '要點', '補款']
# 排除關鍵字：政府資訊公開/行政雜訊，含這些字樣的標題不算補助案
NEG_KW = ['支付或接受', '施政計畫', '業務統計', '旅費', '公務統計', '出國', '考察',
          '利益衝突', '內部控制', '資訊公開', '補助公開', '公開專區', '中長程計畫',
          '統計方案', '執行情形', '聲明書', '快速檢測', '線上申請', '進度查詢', '常見問題']
# 導覽候選連結（往下鑽用）—通往補助清單的入口
NAV_KW  = ['補助', '獎助', '補貼', '獎勵', '計畫', '找補助', '找獎補助', '補助專區',
           '補助資訊', '補助公告', '最新消息', '公告', 'PointList', '清單', '一覽']
LIST_THRESHOLD = 5   # 補助案標題連結 >= 5 → 視為列表頁


def fetch(url):
    r = SESSION.get(url, timeout=18, verify=False)
    if r.status_code in (428, 403):
        pu = urlparse(url)
        try:
            r2 = SESSION.get(url, timeout=18, verify=False,
                             headers={'Referer': f'{pu.scheme}://{pu.netloc}/'})
            if r2.status_code == 200:
                r = r2
        except Exception:
            pass
    r.encoding = r.apparent_encoding or r.encoding
    return r


def list_score(soup):
    """計算頁面像不像補助案列表頁：具體補助標題連結數"""
    titles = []
    for a in soup.find_all('a', href=True):
        t = a.get_text(strip=True)
        if len(t) >= 8 and any(k in t for k in ITEM_KW) and not any(n in t for n in NEG_KW):
            titles.append(t)
    # 去重
    uniq = list(dict.fromkeys(titles))
    return len(uniq), uniq[:5]


def nav_candidates(soup, base):
    host = urlparse(base).netloc
    out, seen = [], set()
    for a in soup.find_all('a', href=True):
        t = a.get_text(strip=True); href = a['href']
        if not t or len(t) < 3:
            continue
        if not any(k in t or k in href for k in NAV_KW):
            continue
        full = urljoin(base, href)
        pu = urlparse(full)
        if pu.scheme not in ('http', 'https') or full in seen:
            continue
        seen.add(full)
        # 短的、像入口的優先（補助專區/找補助），排前面
        priority = 0 if len(t) <= 8 else 1
        out.append((priority, t, full, pu.netloc == host))
    out.sort(key=lambda x: x[0])
    return out


def process(url, category, per, delay):
    res = {'目前是否列表頁': '', '列表項目數': 0, '列表範例': '',
           '建議列表頁網址': '', '建議頁項目數': 0, 'HTTP狀態': '', '備註': ''}
    if not isinstance(url, str) or not url.strip().startswith('http'):
        res['備註'] = '無網址'; return res
    try:
        r = fetch(url); res['HTTP狀態'] = r.status_code
        if r.status_code != 200:
            res['備註'] = f'HTTP {r.status_code}'; return res
        soup = BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        res['HTTP狀態'] = f'error'; res['備註'] = type(e).__name__; return res

    body_len = len(soup.get_text(strip=True))
    score, samples = list_score(soup)
    res['列表項目數'] = score
    res['列表範例'] = ' / '.join(s[:20] for s in samples)

    if score >= LIST_THRESHOLD:
        res['目前是否列表頁'] = '是'
        res['建議列表頁網址'] = r.url
        res['建議頁項目數'] = score
        return res

    # 不是列表頁 → 往下鑽找
    res['目前是否列表頁'] = '否'
    if body_len < 250:
        res['備註'] = '疑似SPA(內文極少)'
    best_url, best_score, best_samples = '', 0, []
    allow_ext = (category == '外部連結彙整')
    cands = nav_candidates(soup, r.url)
    tried = 0
    for pr, t, curl, same in cands:
        if tried >= per:
            break
        if not same and not allow_ext:
            continue
        try:
            time.sleep(delay)
            r2 = fetch(curl); tried += 1
            if r2.status_code != 200:
                continue
            s2 = BeautifulSoup(r2.text, 'html.parser')
            sc2, sm2 = list_score(s2)
            if sc2 > best_score:
                best_score, best_url, best_samples = sc2, r2.url, sm2
        except Exception:
            tried += 1
            continue
    if best_score >= LIST_THRESHOLD:
        res['建議列表頁網址'] = best_url
        res['建議頁項目數'] = best_score
        res['列表範例'] = res['列表範例'] or ' / '.join(s[:20] for s in best_samples)
    else:
        res['備註'] = (res['備註'] + ' 鑽一層仍找不到列表頁').strip()
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cats', type=str, default='申請系統入口,待人工確認,外部連結彙整')
    ap.add_argument('--rows', type=str, default='')
    ap.add_argument('--per', type=int, default=8)
    ap.add_argument('--delay', type=float, default=0.6)
    ap.add_argument('--out', type=str, default=OUT_CSV)
    ap.add_argument('--in', dest='infile', type=str, default=IN_CSV)
    args = ap.parse_args()

    df = pd.read_csv(args.infile, encoding='utf-8-sig')
    if args.rows:
        df = df.loc[[int(x) for x in args.rows.split(',')]]
    else:
        df = df[df['網站類別'].isin(args.cats.split(','))]

    out_rows = []; total = len(df); t0 = time.time()
    for n, (i, row) in enumerate(df.iterrows(), 1):
        url = row.get('網址', ''); cat = row.get('網站類別', ''); name = row.get('機關名稱', '')
        r = process(url, cat, args.per, args.delay)
        if r['目前是否列表頁'] == '是':
            flag = f'✅已是列表頁({r["列表項目數"]}項)'
        elif r['建議列表頁網址']:
            flag = f'🔁鑽到列表頁({r["建議頁項目數"]}項)'
        else:
            flag = f'❌找不到({r["備註"]})'
        print(f'[{n}/{total}] {flag}  {name[:22]}')
        if r['建議列表頁網址'] and r['建議列表頁網址'] != url:
            print(f'         原: {url}')
            print(f'         新: {r["建議列表頁網址"]}')
        out_rows.append({
            '機關名稱': name, '網站類別': cat, '原網址': url,
            '目前是否列表頁': r['目前是否列表頁'], '列表項目數': r['列表項目數'],
            '建議列表頁網址': r['建議列表頁網址'], '建議頁項目數': r['建議頁項目數'],
            '列表範例': r['列表範例'], 'HTTP狀態': r['HTTP狀態'], '備註': r['備註'],
        })
    out_df = pd.DataFrame(out_rows)
    out_df.to_csv(args.out, index=False, encoding='utf-8-sig')
    dt = time.time() - t0
    print(f'\n完成，輸出 {args.out}（{total} 筆，耗時 {dt:.0f} 秒）')
    print('\n目前是否列表頁:'); print(out_df['目前是否列表頁'].value_counts().to_string())
    got = out_df[out_df['建議列表頁網址'] != '']
    print(f'\n有可用列表頁網址: {len(got)}/{total}')


if __name__ == '__main__':
    main()
