# -*- coding: utf-8 -*-
"""
中國生產力中心(CPC) 承辦計畫 → 外部官方網站 申請須知 抓取流程
=================================================================
CPC 本身是「執行/顧問單位」，不是補助機關。它的計畫列表頁
(https://www.cpc.org.tw/zh-tw/post/list/2112) 列出多個計畫，
每個計畫連到 CPC 內頁(post/contents/{id})，內頁再導向各計畫的
「外部官方網站」，申請須知就在那些外部站上。

本腳本流程：
  1. 抓 CPC 計畫列表頁，取出每個計畫卡片(標題 + 內頁連結)
  2. 進每個計畫內頁，抽出它連到的外部官方網站(gov.tw / nat.gov.tw / org.tw)
  3. 對每個外部站嘗試抓「申請須知」PDF
     - 部分站(如 aoc.gov.tw 商業發展署)可穩定抓到
     - 部分站(CITD keid.nat.gov.tw、SIIR gcis.nat.gov.tw/neo-s)是老舊
       ASP.NET WebForms，需 session/viewstate 或已失效，requests 難直接抓

用法： python cpc_programs_crawler.py
需求： pip install requests
"""
import re, html, ssl, sys, io
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
import urllib3; urllib3.disable_warnings()

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-TW,zh;q=0.9',
}

# 政府老舊網站常用舊版 TLS，需降 SECLEVEL 才連得上
class LegacyTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *a, **k):
        ctx = create_urllib3_context()
        try: ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
        except Exception: pass
        ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        k['ssl_context'] = ctx
        return super().init_poolmanager(*a, **k)

def session():
    s = requests.Session(); s.headers.update(HEADERS)
    s.mount('https://', LegacyTLSAdapter())
    return s

def get(s, url, referer=None, timeout=20):
    h = {'Referer': referer} if referer else {}
    r = s.get(url, headers=h, timeout=timeout, verify=False)
    r.encoding = 'utf-8'
    return r

CPC_LIST = 'https://www.cpc.org.tw/zh-tw/post/list/2112'

def step1_list_programs(s):
    """回傳 [(計畫標題, 內頁URL)]"""
    r = get(s, CPC_LIST)
    progs = []
    for card in re.split(r'class="card mb-3', r.text)[1:]:
        m_title = re.search(r'alt="([^"]+)"', card)
        m_link  = re.search(r'href="(/zh-tw/post/contents/\d+)"', card)
        if m_title and m_link:
            progs.append((html.unescape(m_title.group(1)),
                          'https://www.cpc.org.tw' + m_link.group(1)))
    return progs

def step2_external_site(s, contents_url):
    """從計畫內頁抽出外部官方網站(第一個 gov/nat/org 連結)"""
    r = get(s, contents_url)
    ext = re.findall(r'https?://(?!www\.cpc\.org\.tw)[a-zA-Z0-9.\-]+'
                     r'\.(?:gov\.tw|nat\.gov\.tw|org\.tw)[^"\'<> ]*', r.text)
    # 濾掉社群/CDN/schema
    ext = [e for e in ext if not any(x in e for x in
           ('facebook','google','youtube','line','jquery','bootstrap','schema.org'))]
    return sorted(set(ext))

def step3_find_notices(s, site_url):
    """嘗試在外部站首頁及常見下載頁找『申請須知』檔案(檔名/連結)"""
    found = []
    try:
        r = get(s, site_url, referer=site_url)
    except Exception as e:
        return [('抓取失敗', str(e)[:50])]
    # (a) 直接的 pdf/doc 連結且檔名含申請須知
    for m in re.finditer(r'href="([^"]+\.(?:pdf|docx?|odt|zip)[^"]*)"', r.text, re.I):
        fn = html.unescape(m.group(1))
        if '申請須知' in fn:
            found.append(('檔案連結', fn))
    # (b) data-name 屬性(檔名藏在屬性、href 是亂碼時)
    for m in re.finditer(r'data-name="([^"]*申請須知[^"]*)"', r.text):
        found.append(('data-name', html.unescape(m.group(1))))
    # (c) Google Drive 連結 → 解析檔名(標題)，只留檔名含申請須知者
    seen_drive = set()
    for m in re.finditer(r'https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)', r.text):
        fid = m.group(1)
        if fid in seen_drive:
            continue
        seen_drive.add(fid)
        try:
            dr = get(s, f'https://drive.google.com/file/d/{fid}/view')
            mt = re.search(r'<title>(.*?)</title>', dr.text)
            dname = (mt.group(1) if mt else '').replace(' - Google 雲端硬碟', '').strip()
        except Exception:
            dname = ''
        if '申請須知' in dname:
            found.append(('GoogleDrive申請須知', f'{dname}  ({m.group(0)})'))
    # (d) 是否至少有「申請須知」字樣(表示須再深入下載子頁)
    if not found and '申請須知' in r.text:
        found.append(('僅字樣(須進下載子頁)', f'首頁出現{r.text.count("申請須知")}次'))
    return found

def main():
    s = session()
    print('== 步驟1：CPC 計畫列表 ==')
    progs = step1_list_programs(s)
    for t, u in progs:
        print(f'  - {t}  ->  {u}')
    print('\n== 步驟2+3：各計畫外部官方站 + 申請須知 ==')
    for title, curl in progs:
        print(f'\n### {title}')
        sites = step2_external_site(s, curl)
        if not sites:
            print('   (內頁未連到外部官方站，可能由 CPC 分處直接執行)')
            continue
        for site in sites:
            notices = step3_find_notices(s, site)
            print(f'   外部站: {site}')
            for kind, val in notices[:8]:
                print(f'       [{kind}] {val}')

if __name__ == '__main__':
    main()
