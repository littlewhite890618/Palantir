# -*- coding: utf-8 -*-
"""
sites/yunlin.py — 雲林縣 adapter【型態 C / 反偵測 Selenium 繞 Cloudflare】。

雲林縣府站有 Cloudflare，連「找連結」和「下載檔案」都要用反偵測 Selenium。
雲林沒有專屬 SBIR 列表頁，改用「站內關鍵字搜尋」自動發現當年度公告：
    ① 在縣政新聞列表搜「地方型SBIR」→ ② 篩出「當年度＋SBIR＋補助計畫」那則 → 詳情頁
    ③ 進詳情頁抓「相關檔案」裡的 SBIR 公告 PDF
→ 每年自動找到當年度公告，不需手動更新網址。

相關檔案結構：<a href="...Download.ashx?..." data-name="檔名.pdf">pdf</a>（檔名在 data-name）。
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import render, year

DEPARTMENT = "雲林縣"
NEEDS_BROWSER_DOWNLOAD = True   # 告訴 run.py：雲林連下載都要用瀏覽器（檔案也擋 Cloudflare）

BASE = "https://www.yunlin.gov.tw/"
LIST_URL = "https://www.yunlin.gov.tw/News.aspx?n=1244&sms=9662"   # 縣政新聞列表（可關鍵字搜尋）
SEARCH_INPUT = "#jNewsModule_field_0"    # 搜尋框
SEARCH_BTN = "#jNewsModule_BtnSend"      # 送出鈕
KEYWORD = "地方型SBIR"


def _current_announcement_url(html, today=None):
    """從搜尋結果頁找「當年度＋SBIR＋補助計畫」那則公告的詳情連結。"""
    soup = BeautifulSoup(html, "lxml")
    for a in soup.select("a[href*='News_Content']"):
        title = a.get_text(strip=True)
        if year.has_current_year(title, today) and "SBIR" in title and "補助計畫" in title:
            return urljoin(BASE, a["href"])
    return None


def _files(html, today=None):
    """從詳情頁『相關檔案』抓 SBIR 公告檔（檔名在 data-name、連結是 Download.ashx）。"""
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set()
    for a in soup.select("a[href*='Download.ashx'][data-name]"):
        name = a.get("data-name", "").strip()
        url = a["href"]
        if not (year.has_current_year(name, today) and "SBIR" in name):   # 排除地圖等雜項
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append((name, url))
    return out


def find_notices(today=None):
    """搜尋自動發現：搜「地方型SBIR」→ 當年度公告 → 進詳情抓 SBIR 公告檔。回傳 [(檔名, 網址), ...]。"""
    results = render.selenium_search(LIST_URL, SEARCH_INPUT, KEYWORD, SEARCH_BTN)   # ① 搜尋
    detail_url = _current_announcement_url(results, today=today)                    # ② 找當年度公告
    if not detail_url:
        return []
    detail_html = render.selenium_fetch(detail_url)                                 # ③ 進詳情頁
    return _files(detail_html, today=today)                                         # ④ 抓 PDF
