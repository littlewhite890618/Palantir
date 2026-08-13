# -*- coding: utf-8 -*-
"""
sites/tainan.py — 臺南市 adapter【型態 C / 開瀏覽器 render】。

臺南是 SPA（純 requests 只拿到 {{ }} 空殼），且申請文件藏在三層之下、包在 zip 裡：
    ① 入口頁          → 讀「文件下載」選單，找「當前民國年」的連結
    ② 當年度文件頁    → 找「申請階段」的連結
    ③ 申請階段頁      → 收集申請文件 zip（內含申請須知，P3 會解壓）
每一層都是 SPA，都要用 common/render.py 開瀏覽器 render。
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import render, year

DEPARTMENT = "臺南市"
BASE = "https://www.tainan-sbir.org.tw/"
ENTRY_URL = "https://www.tainan-sbir.org.tw/list/news"   # 入口（任一頁都有「文件下載」選單）


def _year_download_url(html):
    """① 從「文件下載」選單找「當前民國年」（例如『115年』）的連結。"""
    roc = year.current_roc_year()
    target = f"{roc}年"
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        # 選單裡年度連結長這樣：<a href="/list/135">115年</a>
        if a.get_text(strip=True) == target and "/list/" in a["href"]:
            return urljoin(BASE, a["href"])
    return None


def _application_stage_url(html):
    """② 從當年度文件頁找「申請階段」項目的連結。"""
    soup = BeautifulSoup(html, "lxml")
    for block in soup.select(".one"):            # 每個 .one = 一個項目
        title = block.select_one(".title")
        link = block.select_one("a.coverlink")
        if title and link and "申請" in title.get_text(strip=True):
            return urljoin(BASE, link.get("href", ""))
    return None


def _files(html):
    """③ 收集申請階段頁的申請文件 zip（= 申請須知所在，內含多份文件）。"""
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/upload/" in href and href.lower().endswith(".zip"):
            url = urljoin(BASE, href)
            if url in seen:                      # 頁面有桌機/手機兩份，去重
                continue
            seen.add(url)
            name = a.get_text(strip=True) or href.rsplit("/", 1)[-1]
            out.append((name, url))
    return out


def find_notices(today=None):
    """三層導航：入口 → 當年度頁 → 申請階段頁 → 申請文件 zip。回傳 [(檔名, 網址), ...]。"""
    year_url = _year_download_url(render.render_html(ENTRY_URL))   # ①
    if not year_url:
        return []
    app_url = _application_stage_url(render.render_html(year_url))  # ②
    if not app_url:
        return []
    return _files(render.render_html(app_url))                     # ③
