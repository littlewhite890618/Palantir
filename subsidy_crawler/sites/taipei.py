# -*- coding: utf-8 -*-
"""
sites/taipei.py — 臺北市 adapter【樣板②：requests，多分類頁、不篩年度】。

臺北市產業獎勵補助是常設計畫（非逐年重辦）。原本只抓 download/1（「申請階段」
父分類），但底下其實還有 6 個獨立的子分類頁面，各自有自己的申請須知：
    創業補助/download/4、研發補助/download/5、品牌建立補助/download/9、
    新創拔尖補助/download/14、創新育成補助/download/10、獎勵補貼/download/15
逐一抓這 6 頁，每頁結構同前：.oneset 區塊，.file_name 是乾淨檔名。
不篩年度，只用 looks_like_notice 篩出「申請須知」類。
※ 這站直接把 bytes 丟給 BeautifulSoup 會被誤判編碼，要先明確 .decode("utf-8")
   成字串，再交給 BeautifulSoup，不能讓它自己猜（同苗栗）。
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, year

DEPARTMENT = "臺北市"
ROOT = "https://www.industry-incentive.taipei/"
DOWNLOAD_URLS = [
    "https://www.industry-incentive.taipei/download/4",   # 創業補助
    "https://www.industry-incentive.taipei/download/5",   # 研發補助
    "https://www.industry-incentive.taipei/download/9",   # 品牌建立補助
    "https://www.industry-incentive.taipei/download/14",  # 新創拔尖補助
    "https://www.industry-incentive.taipei/download/10",  # 創新育成補助
    "https://www.industry-incentive.taipei/download/15",  # 獎勵補貼
]

# 產業發展局 doed（doed.gov.taipei，ASP.NET）：內容頁直接列出各補助計畫的申請須知 PDF
# （附件 title＝檔名帶「[另開新視窗]」前綴，下載走 www-ws.gov.taipei/Download.ashx）。
# 調查結論：檔名不帶年份 → 常設計畫、就地更新（同上方 6 個補助頁），不篩年度、直接抓申請須知。
DOED_ROOT = "https://doed.gov.taipei/"
DOED_URL = DOED_ROOT + "Content_List.aspx?n=EFA24A4D59B05A13"


def _notice_files(html):
    soup = BeautifulSoup(html, "lxml")
    out = []
    for block in soup.select(".oneset"):
        name_el = block.select_one(".file_name")
        link_el = block.select_one("a[href]")
        if name_el is None or link_el is None:
            continue
        name = name_el.get_text(strip=True)
        if year.looks_like_notice(name):
            out.append((name, urljoin(ROOT, link_el["href"])))
    return out


def _doed_notices():
    """doed 內容頁 → 附件 title 含「申請須知」的 PDF（常設、不篩年度）。"""
    soup = BeautifulSoup(http.get(DOED_URL).content, "lxml")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        ti = a.get("title", "").replace("[另開新視窗]", "").strip()
        if "申請須知" in ti and "Download" in a["href"]:
            url = urljoin(DOED_ROOT, a["href"])
            if url not in seen:
                seen.add(url)
                out.append((ti, url))
    return out


def find_notices(today=None):
    out = []
    for url in DOWNLOAD_URLS:
        resp = http.get(url)
        html = resp.content.decode("utf-8", "replace")
        out.extend(_notice_files(html))
    out.extend(_doed_notices())   # 產業發展局 doed 各補助計畫申請須知
    return out
