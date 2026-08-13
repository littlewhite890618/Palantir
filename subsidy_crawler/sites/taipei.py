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


def find_notices(today=None):
    out = []
    for url in DOWNLOAD_URLS:
        resp = http.get(url)
        html = resp.content.decode("utf-8", "replace")
        out.extend(_notice_files(html))
    return out
