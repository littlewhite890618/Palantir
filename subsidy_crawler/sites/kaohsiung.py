# -*- coding: utf-8 -*-
"""
sites/kaohsiung.py — 高雄市 adapter【樣板②：requests + 多層導航】。

高雄的檔案藏在三層下：資料下載 → 當年度高雄市SBIR → 計畫申請階段 → 檔案。
每層都是靜態頁 → 用 http.get（不用瀏覽器）；最底層「檔名＝連結文字」，用 links_from + pick_notices。
導航是「年度動態」：靠 current_roc_year() 找「115年度…SBIR」，明年自動找 116。
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, notice, year

DEPARTMENT = "高雄市"
ROOT = "https://kh-sbir.kcg.gov.tw/"
ENTRY_URL = "https://kh-sbir.kcg.gov.tw/Content_List.aspx?n=62FA45A4D23BD9AA"   # 資料下載


def _find_link(html, text_ok):
    """在 html 裡找第一個「連結文字通過 text_ok() 判斷」的 <a>，回傳絕對網址；找不到回 None。"""
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        if text_ok(a.get_text(strip=True)):
            return urljoin(ROOT, a["href"])
    return None


def find_notices(today=None):
    """三層導航：資料下載 → 當年度SBIR → 計畫申請階段 → 抓當年度須知。"""
    roc = year.current_roc_year()
    # 第①層：資料下載頁 → 找「<roc>年度…SBIR」的連結
    l2 = _find_link(http.get(ENTRY_URL).text, lambda t: f"{roc}年度" in t and "SBIR" in t)
    if not l2:
        return []
    # 第②層：該年度頁 → 找「計畫申請階段」的連結
    l3 = _find_link(http.get(l2).text, lambda t: "申請階段" in t)
    if not l3:
        return []
    # 第③層：檔案頁 → 檔名＝連結文字 → 通用掃法 + 兩把篩子
    return notice.pick_notices(notice.links_from(http.get(l3).text, ROOT), today=today)
