# -*- coding: utf-8 -*-
"""
【樣板：selenium / Cloudflare 反偵測】被 Cloudflare 擋、需反偵測的站。起源：sites/yunlin.py。

特徵：找連結（可能連下載）都要反偵測 Selenium；沒有專屬列表時，用「站內搜尋」自動發現當年度公告。
用法：複製到 sites/<新站>.py → 填空 → run.py 註冊 → 測試。

填空清單：
  ① DEPARTMENT、NEEDS_BROWSER_DOWNLOAD（連下載也擋就 True）
  ② 搜尋設定：LIST_URL、SEARCH_INPUT、SEARCH_BTN、KEYWORD
  ③ _current_announcement_url（挑當年度公告）＋ _files（從詳情抓檔）
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import render, year

DEPARTMENT = "___機關名___"                 # ← ①
NEEDS_BROWSER_DOWNLOAD = True               # 連下載也被 Cloudflare 擋就設 True（否則可刪）

BASE = "___網站根___"
LIST_URL = "___可關鍵字搜尋的列表頁___"       # ← ②
SEARCH_INPUT = "___搜尋框的 CSS 選擇器___"    # 例如 #jNewsModule_field_0
SEARCH_BTN = "___送出鈕的 CSS 選擇器___"      # 例如 #jNewsModule_BtnSend
KEYWORD = "地方型SBIR"


def _current_announcement_url(html, today=None):
    """從搜尋結果頁找「當年度公告」的詳情連結。← ③"""
    soup = BeautifulSoup(html, "lxml")
    # ── 範例（雲林）：篩「當年度 ＋ SBIR ＋ 補助計畫」 ──
    # for a in soup.select("a[href*='News_Content']"):
    #     t = a.get_text(strip=True)
    #     if year.has_current_year(t, today) and "SBIR" in t and "補助計畫" in t:
    #         return urljoin(BASE, a["href"])
    return None


def _files(html, today=None):
    """從詳情頁抓目標檔 [(檔名, 網址), ...]。← ③"""
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set()
    # ── 範例（雲林）：抓 Download.ashx 且 data-name 含（當年度＋SBIR）──
    # for a in soup.select("a[href*='Download.ashx'][data-name]"):
    #     name = a.get("data-name", "").strip()
    #     url = a["href"]
    #     if not (year.has_current_year(name, today) and "SBIR" in name):
    #         continue
    #     if url in seen:
    #         continue
    #     seen.add(url)
    #     out.append((name, url))
    return out


def find_notices(today=None):
    """搜尋自動發現：搜關鍵字 → 當年度公告 → 進詳情抓檔。"""
    results = render.selenium_search(LIST_URL, SEARCH_INPUT, KEYWORD, SEARCH_BTN)
    detail_url = _current_announcement_url(results, today=today)
    if not detail_url:
        return []
    return _files(render.selenium_fetch(detail_url), today=today)
