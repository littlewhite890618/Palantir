# -*- coding: utf-8 -*-
"""
階段0（深鑽版）：對每個 URL 往下鑽（BFS，最多 max_depth 層），
直到在某頁找到「申請須知」PDF。找到就記錄該 PDF 網址 + 所在頁網址（= 更新後網址）。
輸出 deep_probe_result.csv。
"""
import sys, io, time, argparse, ssl, re, warnings
warnings.filterwarnings('ignore')
from collections import deque
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
OUT_CSV = _d('deep_probe_result.csv')

H = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,'
              'image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}


class LegacyTLSAdapter(HTTPAdapter):
    """遷就使用老舊 TLS/加密的政府網站，修正 SSL_error"""
    def init_poolmanager(self, *a, **k):
        ctx = create_urllib3_context()
        ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            ctx.minimum_version = ssl.TLSVersion.TLSv1
        except Exception:
            pass
        k['ssl_context'] = ctx
        return super().init_poolmanager(*a, **k)


def make_session():
    s = requests.Session()
    s.headers.update(H)
    s.mount('https://', LegacyTLSAdapter())
    return s


SESSION = make_session()

SKIP_CATEGORIES = {'無補助業務', '機關首頁'}

# 確認成功用：申請須知 PDF（嚴格）
NOTICE_KW = ['申請須知', '須知']
# 排除：非補助類的「須知」（安全/消防/參觀/志工管理等）
NOTICE_NEG = ['安全管理', '施放', '遶境', '爆竹', '煙火', '參觀須知', '借閱須知',
              '防災', '防疫須知', '注意事項', '乘車', '搭乘', '入園', '登山',
              '志願服務', '志工', '人員管理', '服務人員', '管理須知', '進場', '報名須知',
              '投標', '招標', '火災', '處理流程', '案件處理', '值勤', '勤務', '演習',
              '契約', '議價', '誘拐', '兒少', '預防', '工廠登記', '變更申請', '登記變更']


def url_template(u):
    """URL 樣板：路徑數字→#、只保留 query 鍵。用來判斷兩個 URL 是不是『同格式的兄弟頁』"""
    pu = urlparse(u)
    path = re.sub(r'\d+', '#', pu.path)
    keys = sorted(kv.split('=', 1)[0] for kv in pu.query.split('&') if kv)
    return pu.netloc + path + '?' + ','.join(keys)
# 選擇要跟進哪些連結（廣，依相關度排序）
FOLLOW_KW_HIGH = ['申請須知', '須知', '要點', '簡章', '徵件']       # 最可能通往須知
FOLLOW_KW_LOW  = ['補助', '獎助', '補貼', '計畫', '申請', '公告', '辦法']
DL_MARK = ['download', 'getfile', 'showfile', '.ashx', 'attach', 'fileview', 'openfile']
# 申請須知可接受的檔案格式（不只 PDF）
FILE_EXT = ('.pdf', '.doc', '.docx', '.odt')
# 雲端硬碟連結（也算檔案）
CLOUD = ['drive.google.com', 'docs.google.com', 'dropbox.com', '1drv.ms', 'onedrive.live']


def fetch(url):
    r = SESSION.get(url, timeout=18, verify=False)
    # 428/403 防爬 → 補 Referer 再試一次
    if r.status_code in (428, 403):
        pu = urlparse(url)
        ref = f'{pu.scheme}://{pu.netloc}/'
        try:
            r2 = SESSION.get(url, timeout=18, verify=False, headers={'Referer': ref})
            if r2.status_code == 200:
                r = r2
        except Exception:
            pass
    r.encoding = r.apparent_encoding or r.encoding
    return r


def _is_file_url(low, datafile=''):
    return (low.split('?')[0].endswith(FILE_EXT) or any(m in low for m in DL_MARK)
            or any(c in low for c in CLOUD)
            or (datafile and datafile.split('?')[0].endswith(FILE_EXT)))


def find_notice_pdfs(soup, base):
    """找申請須知檔案：掃 <a> 的 text/href/data-name/data-file/title + 雲端連結；
    也掃任何帶 data-name 的元素（有些站把檔名放 div/span 屬性）。"""
    out = []
    for a in soup.find_all('a', href=True):
        href = a['href']; low = href.lower()
        text = a.get_text(strip=True)
        dname = a.get('data-name', '') or ''
        dfile = (a.get('data-file', '') or '')
        title = a.get('title', '') or a.get('data-original-title', '') or ''
        namestr = ' '.join(x for x in (text, dname, title) if x)
        if not _is_file_url(low, dfile.lower()):
            continue
        # 須知關鍵字必須出現在「檔名/顯示名」（namestr 或實際檔名），不能只在 href query
        basename = href.split('/')[-1].split('?')[0] + ' ' + dfile.split('/')[-1].split('?')[0]
        namecheck = namestr + ' ' + basename
        if not any(k in namecheck for k in NOTICE_KW):
            continue
        if any(n in namecheck for n in NOTICE_NEG):
            continue
        # 實際下載網址：href 若非檔案/雲端，改用 data-file
        fileurl = href
        if not (low.split('?')[0].endswith(FILE_EXT) or any(c in low for c in CLOUD) or any(m in low for m in DL_MARK)):
            if dfile:
                fileurl = dfile
        fname = (dname or text or href.split('/')[-1].split('?')[0]).strip()
        out.append((fname, urljoin(base, fileurl)))
    # 非 <a> 元素但帶 data-name（檔名在屬性、實際檔在 data-file）
    for el in soup.find_all(attrs={'data-name': True}):
        nm = el.get('data-name', '') or ''
        df = el.get('data-file', '') or ''
        if df and any(k in nm for k in NOTICE_KW) and not any(n in nm for n in NOTICE_NEG):
            out.append((nm.strip(), urljoin(base, df)))
    # 去重（同網址只留一次）
    seen = set(); uniq = []
    for n, u in out:
        if u not in seen:
            seen.add(u); uniq.append((n, u))
    return uniq


def candidate_links(soup, base, start_tmpl):
    """回傳 (內部候選, 外部候選)。外部候選＝跳出去的官網（受控）。"""
    host = urlparse(base).netloc
    high, low, ext = [], [], []
    seen = set()
    # 1) 內文「網址：URL」樣式 → 最可能是計畫官網（SIIR 模式），限官方網域
    text_all = soup.get_text(' ', strip=True)
    for m in re.finditer(r'(?:網址|官網|計畫網站|連結)[：:\s]*(https?://[^\s"\'<>）)]+)', text_all):
        u = m.group(1); nl = urlparse(u).netloc
        official = (nl.endswith('gov.tw') or nl.endswith('gov.taipei')
                    or nl.endswith('org.tw') or 'nat.gov' in nl)
        if nl != host and official and u not in seen:
            seen.add(u); ext.append(u)
    for a in soup.find_all('a', href=True):
        href = a['href']; text = a.get_text(strip=True)
        if not text or len(text) < 3:
            continue
        full = urljoin(base, href); pu = urlparse(full)
        if pu.scheme not in ('http', 'https') or full in seen:
            continue
        if url_template(full) == start_tmpl:   # 兄弟頁守衛
            continue
        same = (pu.netloc == host)
        if same:
            if any(k in text for k in FOLLOW_KW_HIGH):
                seen.add(full); high.append(full)
            elif any(k in text for k in FOLLOW_KW_LOW):
                seen.add(full); low.append(full)
        else:
            # 外部：只跟官方網域（gov.tw/gov.taipei/org.tw/nat.gov），避免晃到台電等 .com.tw
            official = (pu.netloc.endswith('gov.tw') or pu.netloc.endswith('gov.taipei')
                        or pu.netloc.endswith('org.tw') or 'nat.gov' in pu.netloc)
            if not official:
                continue
            anchor_is_url = text.lower().startswith(('http', 'www.'))
            relevant = any(k in text for k in FOLLOW_KW_HIGH + FOLLOW_KW_LOW + ['官網', '網站', '系統', '專區'])
            if anchor_is_url or relevant:
                seen.add(full); ext.append(full)
    return high + low, ext


def deep_probe_one(start_url, category, max_depth, max_per_level, budget, delay, max_ext=2):
    """每列都鑽到底找申請須知（不因類別預先跳過）。max_ext=外部跳轉上限（防亂晃）。"""
    res = {
        '找到申請須知': '否', '申請須知PDF檔名': '', '申請須知PDF網址': '',
        '申請須知所在頁網址': '', '找到層級': '', '造訪頁數': 0, 'HTTP狀態': '',
    }
    if not isinstance(start_url, str) or not start_url.strip().startswith('http'):
        res['找到申請須知'] = '否'; res['HTTP狀態'] = 'no_url'; return res

    start_tmpl = url_template(start_url)
    visited = set()
    q = deque([(start_url, 0)])
    used = 0
    ext_used = 0
    first_status = ''
    while q and used < budget:
        cur, d = q.popleft()
        if cur in visited:
            continue
        visited.add(cur)
        try:
            r = fetch(cur); used += 1
            if not first_status:
                first_status = r.status_code
            if r.status_code != 200:
                continue
            soup = BeautifulSoup(r.text, 'html.parser')
        except Exception as e:
            if not first_status:
                first_status = f'error:{type(e).__name__}'
            continue
        time.sleep(delay)
        pdfs = find_notice_pdfs(soup, r.url)
        if pdfs:
            name, purl = pdfs[0]
            res.update({
                '找到申請須知': '是', '申請須知PDF檔名': name[:90], '申請須知PDF網址': purl,
                '申請須知所在頁網址': r.url, '找到層級': d, '造訪頁數': used,
                'HTTP狀態': first_status,
            })
            return res
        if d < max_depth:
            internal, external = candidate_links(soup, r.url, start_tmpl)
            for c in internal[:max_per_level]:
                if c not in visited:
                    q.append((c, d + 1))
            # 外部跳轉受 max_ext 上限保護（避免晃到其他機關官網）
            for c in external:
                if ext_used >= max_ext:
                    break
                if c not in visited:
                    q.append((c, d + 1)); ext_used += 1
    res['造訪頁數'] = used
    res['HTTP狀態'] = first_status
    return res


USER_CSV = _d('探測與分類(第二次分類結果) 3967895cac45806f8b56e4367a39928c_all.csv')
URL_COL = '原網址'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='infile', type=str, default=USER_CSV)
    ap.add_argument('--out', type=str, default=_d('探測與分類_深鑽強化.csv'))
    ap.add_argument('--rows', type=str, default='', help='只跑指定列 index（逗號分隔），測試用')
    ap.add_argument('--depth', type=int, default=3)
    ap.add_argument('--per', type=int, default=6)
    ap.add_argument('--budget', type=int, default=25)
    ap.add_argument('--max-ext', dest='max_ext', type=int, default=2)
    ap.add_argument('--delay', type=float, default=0.7)
    args = ap.parse_args()

    df = pd.read_csv(args.infile, encoding='utf-8-sig')
    # 要重鑽的列：找到申請須知 != 是（否/跳過/待確認/空 都重鑽）；是 的保留不動
    if args.rows:
        targets = [int(x) for x in args.rows.split(',')]
    else:
        targets = [i for i in df.index if str(df.at[i, '找到申請須知']).strip() != '是']

    total = len(targets); t0 = time.time(); newly = 0
    for n, i in enumerate(targets, 1):
        url = df.at[i, URL_COL]; cat = df.at[i, '網站類別']; name = str(df.at[i, '機關名稱'])
        r = deep_probe_one(url, cat, args.depth, args.per, args.budget, args.delay, args.max_ext)
        flag = {'是': '✅', '否': '❌'}.get(r['找到申請須知'], '?')
        print(f'[{n}/{total}] {flag} L{r["找到層級"]} 造訪{r["造訪頁數"]}頁  {name[:24]}')
        if r['找到申請須知'] == '是':
            newly += 1
            print(f'         ⤷ {str(r["申請須知PDF檔名"])[:48]}')
            print(f'         ⤷ {r["申請須知所在頁網址"]}')
        # 寫回該列（是→更新須知欄；否→更新狀態欄，不再標跳過）
        df.at[i, '找到申請須知'] = r['找到申請須知']
        df.at[i, '找到層級'] = r['找到層級']
        df.at[i, '造訪頁數'] = r['造訪頁數']
        df.at[i, 'HTTP狀態'] = r['HTTP狀態']
        if r['找到申請須知'] == '是':
            df.at[i, '申請須知PDF檔名'] = r['申請須知PDF檔名']
            df.at[i, '申請須知PDF網址'] = r['申請須知PDF網址']
            df.at[i, '申請須知所在頁網址（更新後網址）'] = r['申請須知所在頁網址']

    # 交叉誤植偵測（對全表的「是」）
    yes = df[df['找到申請須知'] == '是']
    dup = yes['申請須知PDF網址'].value_counts()
    dup = set(dup[dup > 1].index)
    if dup:
        mask = (df['找到申請須知'] == '是') & (df['申請須知PDF網址'].isin(dup))
        df.loc[mask, '找到申請須知'] = '待確認(疑似交叉)'
        print(f'\n⚠️ 交叉誤植：{mask.sum()} 列共用 {len(dup)} 份檔案，標記待確認')

    df.to_csv(args.out, index=False, encoding='utf-8-sig')
    dt = time.time() - t0
    print(f'\n完成，輸出 {args.out}')
    print(f'重鑽 {total} 列，新找到申請須知 {newly} 筆，耗時 {dt:.0f} 秒')
    print('\n全表 找到申請須知 分佈:'); print(df['找到申請須知'].value_counts().to_string())


if __name__ == '__main__':
    main()
