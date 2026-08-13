# -*- coding: utf-8 -*-
"""
sites/hsinchu_city.py — 新竹市 adapter【型態 A / requests】。

下載頁 /download/{民國年} 直接列出檔案；連結文字是「pdf/doc」（格式標籤），
真正檔名放在 title 屬性 → 直接讀 title。年度動態，明年自動 116。
※ 該站 SSL 憑證需 verify off，已由 http.py 的 LegacyTLSAdapter 處理。
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, notice, year

DEPARTMENT = "新竹市"
ROOT = "https://www.hccitysbir.org/"


def _candidates(html):
    """新竹市：連結文字是「pdf/doc」，檔名在 title 屬性（連結含 filedownload）。"""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        if "filedownload" in a["href"]:
            name = a.get("title", "").strip()
            out.append((name, urljoin(ROOT, a["href"])))
    return out


def find_notices(today=None):
    roc = year.current_roc_year()
    resp = http.get(f"{ROOT}download/{roc}")      # 例：/download/115
    return notice.pick_notices(_candidates(resp.text), today=today)
