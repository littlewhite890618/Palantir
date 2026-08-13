# -*- coding: utf-8 -*-
"""
sites/taoyuan.py — 桃園市 adapter【樣板②：requests，單頁多筆】。

新聞頁（/news）是 SPA，render 也拓不到列表內容，原因不明。改用「檔案下載」頁
（/download/1，申請須知及附件），純 requests 就抓得到，不用開瀏覽器。
每個檔案是一個 li.news-group：連結（<a>）沒有文字，檔名在旁邊的
<h5 class="news-heading">（同金門「檔名在另一個元素」的模式）。
檔名清楚標年度（如「115年SBIR申請須知」），篩選：當年度 + 像須知。
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, year

DEPARTMENT = "桃園市"
ROOT = "https://taoyuan-sbir.tw/"
DOWNLOAD_URL = "https://taoyuan-sbir.tw/download/1"


def find_notices(today=None):
    resp = http.get(DOWNLOAD_URL)
    soup = BeautifulSoup(resp.content, "lxml")
    out = []
    for li in soup.select("li.news-group"):
        a = li.select_one("a[href]")
        name_el = li.select_one(".news-heading")
        if a is None or name_el is None:
            continue
        name = name_el.get_text(strip=True)
        if year.has_current_year(name, today) and year.looks_like_notice(name):
            out.append((name, urljoin(ROOT, a["href"])))
    return out
