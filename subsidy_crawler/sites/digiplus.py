# -*- coding: utf-8 -*-
"""
sites/digiplus.py — 數位發展部 DIGITAL+數位創新補助平台 adapter【SPA render + 單頁多筆】。

新聞列表頁是 JS 動態分頁（換頁連結都是 #，render 抓不到實際項目）。改用
「文件下載」頁（data_download_n.html）——這是給申請人「現在」下載文件用的服務頁，
各計畫檔名自帶年度標籤（如「115年度數位新創應用獎勵計畫-申請須知.pdf」），
網址固定不變，明年會換成116年度的檔案，靠篩選邏輯自動跟著換，不用改程式。
連結文字只是「pdf檔/odt檔」格式標籤，真正檔名在 title（尾巴多了「(下載)」要清掉）。
"""
import re
from bs4 import BeautifulSoup

from ..common import render, year

DEPARTMENT = "數位發展部"
DOWNLOAD_URL = "https://digiplus.adi.gov.tw/data_download_n.html"


def _clean_title(title):
    """title 格式："檔名.pdf(下載)" → 去掉尾巴的 "(下載)"。"""
    return re.sub(r"\(下載\)\s*$", "", title).strip()


def find_notices(today=None):
    html = render.render_html(DOWNLOAD_URL, timeout=60000)
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        if "contentDownload" not in a["href"]:
            continue
        name = _clean_title(a.get("title", "")) or a.get_text(strip=True)
        if year.has_current_year(name, today) and year.looks_like_notice(name):
            out.append((name, a["href"]))
    return out
