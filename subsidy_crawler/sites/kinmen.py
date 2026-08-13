# -*- coding: utf-8 -*-
"""
sites/kinmen.py — 金門縣 adapter【型態 A / 一般連線 requests】。

金門下載區的結構（每個檔案是一張 card）：
    <div id="section-download">
      <div class="card">
        <div class="txt">115年金門SBIR申請須知</div>        ← 檔名在這
        <a href="index.php?...op=download&id=195">下載</a>   ← 連結在這（文字只是「下載」）
      </div>
      ...
    </div>
因為「檔名」和「連結」不在同一個標籤，不能用通用的 links_from，要自己配對。
"""
from bs4 import BeautifulSoup

from ..common import http, notice

DEPARTMENT = "金門縣"
LIST_URL = "https://kinmensbir.org.tw/index.php"


def _candidates(html):
    """從金門下載區 HTML，湊出 [(檔名, 絕對網址), ...]。"""
    soup = BeautifulSoup(html, "lxml")
    out = []
    section = soup.find(id="section-download")   # 先鎖定「資料下載」那一區
    if section is None:
        return out
    for card in section.select(".card"):         # 該區裡每一張 card = 一個檔案
        txt = card.select_one(".txt")            # 檔名所在
        link = card.select_one("a[href]")        # 下載連結所在
        if txt is None or link is None:
            continue
        name = txt.get_text(strip=True)
        url = notice.absolute(LIST_URL, link["href"])
        out.append((name, url))
    return out


def find_notices(today=None):
    """抓金門下載頁 → 湊候選 → 篩出「當年度的申請須知」。回傳 [(檔名, 網址), ...]。"""
    resp = http.get(LIST_URL)                     # ① 用 http 抓頁面
    candidates = _candidates(resp.text)           # ② 從 HTML 湊出所有檔案
    return notice.pick_notices(candidates, today=today)  # ③ 篩出當年度須知
