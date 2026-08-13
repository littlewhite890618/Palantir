# -*- coding: utf-8 -*-
"""
sites/trade.py — 國際貿易署 adapter【內建搜尋 API + 單頁多筆】。

這站的列表頁（Pages/List.aspx?nodeID=39）用 AJAX 打站內搜尋 API：
    GET /App_Ashx/getDataByNodeid.ashx?nodeID=..&keyword=..&datatime=all&pageindex=1
    （要帶 X-Requested-With + Referer，否則伺服器當一般網頁請求處理、回傳整頁HTML而非JSON）
直接呼叫這個 API 搜「申請須知」，不用開瀏覽器，拿到 JSON 裡的 Html 片段解析。

附件本身檔名是無意義代碼（如「115D2003757-01.pdf」），不像其他站有描述性檔名，
所以不能靠 looks_like_notice 篩附件檔名——改成：搜尋結果的「公告標題」本身就
含「申請須知」+ 當年度（伺服器端關鍵字已篩過，這裡只再篩年度），公告底下的
附件就直接收（用公告標題當檔名，比原始代碼名更有意義）。
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, year

DEPARTMENT = "國際貿易署"
ROOT = "https://www.trade.gov.tw/"
LIST_PAGE = "https://www.trade.gov.tw/Pages/List.aspx?nodeID=39"
SEARCH_API = "https://www.trade.gov.tw/App_Ashx/getDataByNodeid.ashx"
NODE_ID = "39"
KEYWORD = "申請須知"


def _search(today=None):
    """呼叫搜尋 API → 篩「當年度」的公告 → 回傳 [(公告標題, 詳情網址), ...]。"""
    params = {
        "nodeID": NODE_ID, "keyword": KEYWORD,
        "calendarTo": "", "calendarFrom": "", "history": "",
        "datatime": "all", "pageindex": "1",
    }
    headers = {"X-Requested-With": "XMLHttpRequest", "Referer": LIST_PAGE}
    resp = http.get(SEARCH_API, params=params, headers=headers, timeout=25)
    data = resp.json()
    soup = BeautifulSoup(data.get("Html", ""), "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        title = a.get_text(strip=True)
        if not title or not year.has_current_year(title, today):
            continue
        out.append((title, urljoin(ROOT, a["href"])))
    return out


def _attachment_files(html, announcement_title):
    """詳情頁 .attachment-list 裡的附件 → 用公告標題當檔名（附件本身只有代碼名）。"""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.select(".attachment-list a[href]"):
        href = a["href"]
        if "File.ashx" not in href:
            continue
        code_name = a.get("title", "").strip() or a.get_text(strip=True)
        ext = code_name.rsplit(".", 1)[-1] if "." in code_name else ""
        name = f"{announcement_title}.{ext}" if ext else announcement_title
        out.append((name, urljoin(ROOT, href)))
    return out


def find_notices(today=None):
    out = []
    for title, durl in _search(today=today):
        detail_html = http.get(durl).text
        out.extend(_attachment_files(detail_html, title))
    return out
