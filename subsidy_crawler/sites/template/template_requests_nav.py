# -*- coding: utf-8 -*-
"""
【樣板②：requests + 多層導航】靜態站，但檔案藏在多層下（要一層層點進去）。起源：sites/kaohsiung.py。
也涵蓋「型態 B（列表→詳情）」——把導航改成 2 層即可。

用法：複製到 sites/<新站>.py → 填空 → run.py 註冊 → 測試。

填空清單：
  ① DEPARTMENT / ROOT / ENTRY_URL
  ② find_notices 內的「導航」：每層 http.get + _find_link（傳一個 lambda 條件）找到下一層網址
  ③ 最底層抓檔：檔名＝連結文字 → links_from + pick_notices；藏它處則自寫 _files
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, notice, year

DEPARTMENT = "___機關名___"                 # ← ①
ROOT = "___網站根___"                       # 補相對網址用，例如 https://www.xxx.gov.tw/
ENTRY_URL = "___導航起點頁___"              # ← 第一層入口


def _find_link(html, text_ok):
    """在 html 找第一個「文字通過 text_ok() 判斷」的 <a>，回傳絕對網址；找不到回 None。（通用小幫手，不用改）"""
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        if text_ok(a.get_text(strip=True)):
            return urljoin(ROOT, a["href"])
    return None


def find_notices(today=None):
    """多層導航：每層 http.get + _find_link 找下一層 → 最底層抓檔。← ② 依該站層數/條件改。"""
    roc = year.current_roc_year()
    # ── 範例（高雄 三層）：把下面取消註解、依該站改條件 ──
    # l2 = _find_link(http.get(ENTRY_URL).text, lambda t: f"{roc}年度" in t and "SBIR" in t)
    # if not l2:
    #     return []
    # l3 = _find_link(http.get(l2).text, lambda t: "申請階段" in t)
    # if not l3:
    #     return []
    # return notice.pick_notices(notice.links_from(http.get(l3).text, ROOT), today=today)
    return []
