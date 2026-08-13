# -*- coding: utf-8 -*-
"""
sites/aoc.py — 經濟部商業發展署 adapter【內建搜尋(POST) + 多筆詳情】。

跟產發署/中小企業署同款「中央站：多個不同補助計畫並存」。這站「訊息公告」
（publicList/2）有自己的篩選表單（POST 回原網址），欄位：
    keyword（關鍵字）、beginMonth/endMonth（西元年月範圍，如"2026-01"）、
    pageCount（只能是10/20/30，其他值會讓查詢失效）
用 keyword=須知類關鍵字（見 KEYWORDS）+ beginMonth=當年度1月 篩出當年度的須知類
公告，不用瀏覽器（純 requests 就不擋）。
※ 年度篩選交給伺服器端的 beginMonth（很多公告標題本身沒有年份字樣，
   不能靠標題篩年度，例如「提升商業服務業營運效能強化韌性計畫」整合型補助
   申請須知——沒有「115」但確實是當年度公告）。
※ 關鍵字不只「申請須知」：少數計畫標題用別的命名（品牌價值計畫叫「輔導徵選須知」），
   在 KEYWORDS 逐一補上、逐關鍵字各自搜一輪再合併去重（見 _search）。
※ 重要：paginationPage 是「從 0 開始算」（0=第1頁，1=第2頁…），一開始
   誤用 "1" 當第一頁，結果整個跳過真正的第一頁（18筆全部漏掉，只剩第二
   頁的7筆）。回應頁面本身有分頁按鈕（class="page-item"，其中一個帶
   active）可以核對目前在第幾頁；「下一頁」按鈕若帶 disabled 代表沒有下一頁了。
流程：
  ① 從 paginationPage=0 開始，逐頁 POST 搜尋，直到某頁抓不到任何結果為止
  ② 詳情頁 → 附件連結（/showPublicAttach/ID）文字本身就是完整檔名
     → looks_like_notice 篩須知類
"""
from datetime import date
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, year

DEPARTMENT = "經濟部商業發展署"
ROOT = "https://www.aoc.gov.tw/"
LIST_URL = "https://www.aoc.gov.tw/publicList/2"
# 站內搜尋用的關鍵字（公告標題含這些字才會被伺服器回傳）。多數計畫標題叫「申請須知」，
# 但少數用別的命名（例如品牌價值計畫叫「輔導徵選須知」），逐一補進來精準撈回，
# 不放寬成「須知」是因為那會混進一堆甄選/競賽公告。
KEYWORDS = ["申請須知", "輔導徵選須知"]
_MAX_PAGES = 20   # 安全上限，避免萬一停止條件失效造成無窮迴圈


def _search_page(keyword, page, today=None):
    """POST 搜尋「keyword」+ 當年度起，抓「單一頁」→ 回傳 [(公告標題, 詳情網址), ...]。"""
    d = today or date.today()
    resp = http.post(LIST_URL, data={
        "keyword": keyword,
        "beginMonth": f"{d.year}-01",
        "endMonth": "",
        "pageCount": "30",           # 只能是 10/20/30
        "paginationPage": str(page),  # 從 0 開始算
    })
    soup = BeautifulSoup(resp.content.decode("utf-8", "replace"), "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/showPublic/" not in href:
            continue
        title = a.get_text(strip=True)
        if not title:
            continue
        out.append((title, urljoin(ROOT, href)))
    return out


def _search(today=None):
    """逐關鍵字、逐頁抓（paginationPage 從 0 起算），合併並以詳情網址去重。"""
    out, seen = [], set()
    for keyword in KEYWORDS:
        for page in range(_MAX_PAGES):
            page_results = _search_page(keyword, page, today=today)
            if not page_results:
                break   # 這個關鍵字翻完了，換下一個關鍵字
            for title, url in page_results:
                if url not in seen:
                    seen.add(url)
                    out.append((title, url))
    return out


def _notice_files(html):
    """詳情頁附件（/showPublicAttach/ID）→ 連結文字本身就是完整檔名 → 篩須知類。"""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        if "/showPublicAttach/" not in a["href"]:
            continue
        name = a.get_text(strip=True) or a.get("title", "")
        if year.looks_like_notice(name):
            out.append((name, urljoin(ROOT, a["href"])))
    return out


def find_notices(today=None):
    out = []
    for _title, durl in _search(today=today):
        detail_html = http.get(durl).content.decode("utf-8", "replace")
        out.extend(_notice_files(detail_html))
    return out
