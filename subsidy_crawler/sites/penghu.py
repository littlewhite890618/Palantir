# -*- coding: utf-8 -*-
"""
sites/penghu.py — 澎湖縣 adapter【型態 A / requests / 檔名在網址路徑】。

澎湖下載頁的檔案直接列出，但連結文字都是「下載」，真正檔名在網址裡
（/docs/DownloadPage/115年申請須知.docx）。所以從 href 取檔名，再交 pick_notices 篩。
"""
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup

from ..common import http, notice

DEPARTMENT = "澎湖縣"
ROOT = "https://www.phsbir.com.tw/"
LIST_URL = "https://www.phsbir.com.tw/Home/Downloads"


def _candidates(html):
    """澎湖：檔名在網址最後一段（連結文字只是「下載」）。"""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/DownloadPage/" in href:                    # 澎湖的檔案連結特徵
            name = unquote(href.rsplit("/", 1)[-1])     # 取網址最後一段當檔名
            out.append((name, urljoin(ROOT, href)))
    return out


def find_notices(today=None):
    resp = http.get(LIST_URL)
    return notice.pick_notices(_candidates(resp.text), today=today)
