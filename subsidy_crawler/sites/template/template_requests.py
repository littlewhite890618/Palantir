# -*- coding: utf-8 -*-
"""
【樣板：requests / 型態 A】固定下載頁的站。起源：sites/kinmen.py。

用法：把這支複製到 sites/<新站>.py → 填三個空格 → 到 run.py 的 SITES 註冊 → 測試。
（本檔在 sites/template/ 下，只供複製參考、不會被 run.py 匯入執行；
  import 路徑是以「複製後放在 sites/<新站>.py」的位置寫的。）

填空清單：
  ① DEPARTMENT   機關名（字串）
  ② LIST_URL     固定下載頁網址
  ③ _candidates  這站怎麼從 HTML 湊出 [(檔名, 連結)]（依該站 HTML 結構改寫）
"""
from bs4 import BeautifulSoup

from ..common import http, notice

DEPARTMENT = "___機關名___"                 # ← ①
LIST_URL = "___固定下載頁網址___"            # ← ②


def _candidates(html):
    """從下載頁 HTML 湊出 [(檔名, 絕對網址), ...]。← ③ 依該站結構改寫。"""
    soup = BeautifulSoup(html, "lxml")
    out = []
    # ── 範例（金門）：鎖定下載區 → 每張卡片取「檔名 + 連結」 ──
    # section = soup.find(id="section-download")
    # if section is None:
    #     return out
    # for card in section.select(".card"):
    #     txt = card.select_one(".txt")
    #     link = card.select_one("a[href]")
    #     if txt is None or link is None:
    #         continue
    #     name = txt.get_text(strip=True)
    #     url = notice.absolute(LIST_URL, link["href"])
    #     out.append((name, url))
    return out


def find_notices(today=None):
    """骨架固定，通常不用改：抓頁 → 湊候選 → 用（年度＋須知）兩把篩子篩。"""
    resp = http.get(LIST_URL)
    candidates = _candidates(resp.text)
    return notice.pick_notices(candidates, today=today)
