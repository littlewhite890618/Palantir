# -*- coding: utf-8 -*-
"""
【樣板：render / SPA】內容要 JavaScript 才長出來的站。起源：sites/tainan.py。

特徵：純 requests 只拿到空殼，每一層都要 render.render_html（開瀏覽器）。
用法：複製到 sites/<新站>.py → 填空 → run.py 註冊 → 測試。

填空清單：
  ① DEPARTMENT / BASE / ENTRY_URL
  ② find_notices 內的「導航」：依該站層數，一層層 render + 解析出下一層網址
  ③ _files       最底層怎麼挑出目標檔
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import render, year

DEPARTMENT = "___機關名___"                 # ← ①
BASE = "___網站根___"                       # 補相對網址用，例如 https://www.xxx.org.tw/
ENTRY_URL = "___入口頁___"                  # ← 導航起點


def _files(html, today=None):
    """從最底層頁面挑出目標檔 [(檔名, 網址), ...]。← ③"""
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set()
    # ── 範例（臺南）：挑 /upload/*.zip、去重 ──
    # for a in soup.find_all("a", href=True):
    #     href = a["href"]
    #     if "/upload/" in href and href.lower().endswith(".zip"):
    #         url = urljoin(BASE, href)
    #         if url in seen:
    #             continue
    #         seen.add(url)
    #         name = a.get_text(strip=True) or href.rsplit("/", 1)[-1]
    #         out.append((name, url))
    return out


def find_notices(today=None):
    """導航：render 每一層 → 找到通往下一層的連結 → 最底層抓檔。← ② 依該站層數改。"""
    html = render.render_html(ENTRY_URL)
    # ── 範例（臺南 三層）──
    # roc = year.current_roc_year()
    # 第①層：從選單找「<roc>年」連結 → year_url
    # 第②層：render(year_url) 找「申請階段」連結 → app_url
    # 第③層：html = render.render_html(app_url)
    return _files(html, today=today)
