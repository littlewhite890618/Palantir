# -*- coding: utf-8 -*-
"""
sites/keelung.py — 基隆市 adapter【樣板②變體：requests + 站內搜尋(POST) + 多筆詳情】。

基隆沒有專屬 SBIR 列表，用站內搜尋（POST，欄位 q_stitle）搜「地方型SBIR」，
取得跨年度所有相關公告；不試著猜哪篇是「徵件公告」，而是對每篇詳情頁的附件
都用（當年度＋須知）篩選——只有真的帶申請須知附件的那篇會被收進來，更穩健。
附件連結文字只是格式標籤（如「ODT」），真正檔名在 title 屬性。
這站宣告編碼會誤判，一律用 .content 交給 BeautifulSoup 自動偵測。
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, year

DEPARTMENT = "基隆市"
SEARCH_URL = "https://www.klcg.gov.tw/tw/economy/2627.html"
KEYWORD = "地方型SBIR"


def _soup(resp):
    return BeautifulSoup(resp.content, "lxml")


def _search_result_links(soup):
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        t = a.get_text(strip=True)
        href = a["href"]
        if "SBIR" in t and "economy/2627-" in href:
            url = urljoin(SEARCH_URL, href)
            if url not in seen:
                seen.add(url)
                out.append(url)
    return out


def _notice_attachments(soup, today=None):
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "Attachment" not in href:
            continue
        name = a.get("title", "").strip() or a.get_text(strip=True)
        if year.has_current_year(name, today) and year.looks_like_notice(name):
            out.append((name, urljoin(SEARCH_URL, href)))
    return out


def find_notices(today=None):
    resp = http.post(SEARCH_URL, data={"q_stitle": KEYWORD, "nowPage": "1", "pageSize": "20"})
    detail_urls = _search_result_links(_soup(resp))
    out = []
    for durl in detail_urls:
        out.extend(_notice_attachments(_soup(http.get(durl)), today=today))
    return out
