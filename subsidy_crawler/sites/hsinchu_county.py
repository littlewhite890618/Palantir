# -*- coding: utf-8 -*-
"""
sites/hsinchu_county.py — 新竹縣 adapter【樣板②：requests + 三層導航】。

三層（皆靜態頁 http.get）：
  ① 首頁 → 找「下載專區」連結
  ② 下載專區 → 找「<roc>年計畫申請文件」連結
  ③ 該頁 → 檔名＝連結文字（如「115年度新竹縣地方型SBIR申請須知」）→ links_from + pick_notices
年度動態：靠 current_roc_year()，明年自動找 116。
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, notice, year

DEPARTMENT = "新竹縣"
ROOT = "https://hchg-sbir.org/"


def _find_link(html, text_ok):
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        if text_ok(a.get_text(strip=True)):
            return urljoin(ROOT, a["href"])
    return None


def find_notices(today=None):
    roc = year.current_roc_year()
    l2 = _find_link(http.get(ROOT).text, lambda t: t == "下載專區")
    if not l2:
        return []
    l3 = _find_link(http.get(l2).text, lambda t: f"{roc}年計畫申請文件" in t)
    if not l3:
        return []
    return notice.pick_notices(notice.links_from(http.get(l3).text, ROOT), today=today)
