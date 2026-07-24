# -*- coding: utf-8 -*-
"""
階段0：探測與分類
對每個 URL 探測 HTTP 狀態、技術類型、頁面型態、是否含申請須知 PDF、可自動化程度。
輸出 probe_result.csv（不抓補助內容，只分類）。
"""
import sys, io, time, argparse
import requests
from bs4 import BeautifulSoup
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os
_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
def _d(name):
    return os.path.join(_DATA, name)

IN_CSV  = _d('政府官方平台資料庫_整理版v4.csv')
OUT_CSV = _d('probe_result.csv')

NOTICE_KEYWORDS = ['申請須知', '須知']

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/122.0 Safari/537.36',
    'Accept-Language': 'zh-TW,zh;q=0.9',
}

# 不需爬取的網站類別 → 直接跳過
SKIP_CATEGORIES = {'無補助業務', '機關首頁'}


# 下載處理器特徵（非 .pdf 結尾，但可能是檔案下載）
DOWNLOAD_MARKERS = ['download', 'getfile', 'showfile', '.ashx', 'attach', 'fileview', 'openfile']
# 深層詳情頁特徵（點進去才有 PDF）
DETAIL_MARKERS = ['docdetail', 'detail.aspx', 'content_detail', 'newsdetail', 'p_detail']


def find_notice_pdfs(soup, base_url):
    """回傳頁內符合申請須知關鍵字的直接 PDF 連結 [(檔名, 完整url), ...]"""
    from urllib.parse import urljoin
    found = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True)
        low = href.lower()
        # 直接 .pdf 連結，或下載處理器連結，且文字/href 含關鍵字
        is_pdf = low.endswith('.pdf')
        is_dl = any(m in low for m in DOWNLOAD_MARKERS)
        kw_hit = any(k in text or k in href for k in NOTICE_KEYWORDS)
        if (is_pdf or is_dl) and kw_hit:
            full = urljoin(base_url, href)
            fname = href.split('/')[-1].split('?')[0] or text
            label = text if text else fname
            found.append((label, full))
    return found


def has_deep_notice_hint(soup):
    """頁面是否有『須知/要點/補助』字樣的詳情頁連結（PDF 可能在下一層）"""
    for a in soup.find_all('a', href=True):
        low = a['href'].lower()
        text = a.get_text(strip=True)
        if any(m in low for m in DETAIL_MARKERS):
            if any(k in text for k in ['須知', '要點', '補助', '獎助', '簡章', '計畫']):
                return True
    return False


def detect_tech_type(resp, soup, body_text_len):
    """粗略判斷技術類型"""
    ct = resp.headers.get('Content-Type', '').lower()
    if 'pdf' in ct:
        return 'PDF'
    # SPA 特徵：有 root div 但 body 文字極少
    spa_markers = soup.find(id='root') or soup.find(id='app') or soup.find('div', {'ng-app': True})
    if body_text_len < 200 and (spa_markers or '<script' in resp.text.lower()):
        return 'SPA'
    if body_text_len < 200:
        return 'SPA'
    # 靜態 vs 動態：URL 含 .html 且無 query 傾向靜態；有 .aspx/.jsp/.php 或 query 為動態
    url = resp.url.lower()
    if any(x in url for x in ['.aspx', '.jsp', '.php', '?', 'news', 'content']):
        return '動態(SSR)'
    if url.endswith('.html') or url.endswith('.htm'):
        return '靜態'
    return '動態(SSR)'


def detect_page_type(soup, body_text_len):
    """粗略判斷頁面型態"""
    # 清單頁：有很多列表項或多個連結群
    links = soup.find_all('a', href=True)
    list_items = soup.find_all('li')
    if len(list_items) > 15 or len(links) > 40:
        return '清單頁'
    if body_text_len < 200:
        return '無法判斷'
    if len(links) < 10:
        return '單一計畫頁'
    return '清單頁'


def probe_one(url, category):
    """探測單一 URL，回傳 dict"""
    result = {
        'HTTP狀態': '', '技術類型': '', '頁面型態': '',
        '含申請須知PDF': '否', '深層文件線索': '否', '可自動化': '低',
        '申請須知PDF清單': '',
    }
    if category in SKIP_CATEGORIES:
        result['HTTP狀態'] = 'skip'
        result['技術類型'] = '跳過'
        result['頁面型態'] = category
        result['可自動化'] = '低'
        return result
    if not isinstance(url, str) or not url.strip().startswith('http'):
        result['HTTP狀態'] = 'no_url'
        result['技術類型'] = '連線失敗'
        return result
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
        result['HTTP狀態'] = resp.status_code
        if resp.status_code != 200:
            result['技術類型'] = '連線失敗'
            return result
        resp.encoding = resp.apparent_encoding or resp.encoding
        soup = BeautifulSoup(resp.text, 'html.parser')
        body_text = soup.get_text(separator=' ', strip=True)
        blen = len(body_text)
        result['技術類型'] = detect_tech_type(resp, soup, blen)
        result['頁面型態'] = detect_page_type(soup, blen)
        pdfs = find_notice_pdfs(soup, resp.url)
        if pdfs:
            result['含申請須知PDF'] = '是'
            result['申請須知PDF清單'] = ' | '.join(f'{n}::{u}' for n, u in pdfs)
        if has_deep_notice_hint(soup):
            result['深層文件線索'] = '是'
        # 可自動化評分
        if result['技術類型'] in ('動態(SSR)', '靜態') and result['含申請須知PDF'] == '是':
            result['可自動化'] = '高'          # 直接抓得到 PDF
        elif result['深層文件線索'] == '是':
            result['可自動化'] = '中'          # 需往下一層爬
        elif result['技術類型'] in ('動態(SSR)', '靜態'):
            result['可自動化'] = '中'
        else:
            result['可自動化'] = '低'
    except requests.exceptions.SSLError:
        result['HTTP狀態'] = 'SSL_error'
        result['技術類型'] = '連線失敗'
    except requests.exceptions.Timeout:
        result['HTTP狀態'] = 'timeout'
        result['技術類型'] = '連線失敗'
    except Exception as e:
        result['HTTP狀態'] = f'error:{type(e).__name__}'
        result['技術類型'] = '連線失敗'
    return result


def main():
    global IN_CSV, SKIP_CATEGORIES
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0, help='只跑前 N 筆（0=全部）')
    ap.add_argument('--rows', type=str, default='', help='指定列 index，逗號分隔')
    ap.add_argument('--delay', type=float, default=1.5, help='每請求間隔秒數')
    ap.add_argument('--force', action='store_true', help='忽略跳過類別，強制爬取')
    ap.add_argument('--out', type=str, default=OUT_CSV, help='輸出檔路徑')
    ap.add_argument('--in', dest='infile', type=str, default=IN_CSV, help='輸入檔路徑')
    args = ap.parse_args()

    IN_CSV = args.infile
    if args.force:
        SKIP_CATEGORIES = set()

    import urllib3
    urllib3.disable_warnings()

    df = pd.read_csv(IN_CSV, encoding='utf-8-sig')

    if args.rows:
        idxs = [int(x) for x in args.rows.split(',')]
        df = df.loc[idxs]
    elif args.limit > 0:
        df = df.head(args.limit)

    out_rows = []
    total = len(df)
    for n, (i, row) in enumerate(df.iterrows(), 1):
        url = row.get('網址', '')
        cat = row.get('網站類別', '')
        name = row.get('機關名稱', '')
        r = probe_one(url, cat)
        print(f'[{n}/{total}] {name[:20]:<20} {str(r["HTTP狀態"]):<8} '
              f'{r["技術類型"]:<10} {r["頁面型態"]:<8} PDF={r["含申請須知PDF"]} '
              f'深層={r["深層文件線索"]} 自動化={r["可自動化"]}')
        out_rows.append({
            '機關名稱': name, '網址': url, '網站類別': cat,
            'HTTP狀態': r['HTTP狀態'], '技術類型': r['技術類型'],
            '頁面型態': r['頁面型態'], '含申請須知PDF': r['含申請須知PDF'],
            '深層文件線索': r['深層文件線索'],
            '可自動化': r['可自動化'], '申請須知PDF清單': r['申請須知PDF清單'],
        })
        if r['HTTP狀態'] not in ('skip', 'no_url'):
            time.sleep(args.delay)

    out_df = pd.DataFrame(out_rows)
    out_df.to_csv(args.out, index=False, encoding='utf-8-sig')
    print(f'\n完成，輸出 {args.out}（{len(out_df)} 筆）')
    print('\n--- 統計 ---')
    print('技術類型:'); print(out_df['技術類型'].value_counts().to_string())
    print('\n含申請須知PDF(直接):'); print(out_df['含申請須知PDF'].value_counts().to_string())
    print('\n深層文件線索:'); print(out_df['深層文件線索'].value_counts().to_string())
    print('\n可自動化:'); print(out_df['可自動化'].value_counts().to_string())


if __name__ == '__main__':
    main()
