# -*- coding: utf-8 -*-
"""
sites/nantou.py — 南投縣 adapter【樣板②：requests + 多層導航】。

三層導航（皆靜態頁 http.get）：
  ① 專區入口（各年度列表）→ 找「當年度…SBIR專區」
  ② 當年度SBIR專區 → 找「…SBIR申請須知」那則公告（連到詳情）
  ③ 公告詳情頁 → 檔名＝連結文字 → links_from + pick_notices（會抓到 pdf 與 docx 兩版）
年度動態：靠 current_roc_year()，明年自動找 116。
"""
from ..common import http, notice, year
from bs4 import BeautifulSoup
from urllib.parse import urljoin

DEPARTMENT = "南投縣"
ROOT = "https://www.nantou.gov.tw/big5/bureau/"     # 所有頁都在這層，補相對網址用
ENTRY_URL = "https://www.nantou.gov.tw/big5/bureau/category_list.php?dptid=376480000au180000&cid=1969"


def _find_link(html, text_ok):
    """在 html 找第一個「文字通過 text_ok」的 <a>，回傳絕對網址；找不到回 None。"""
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        if text_ok(a.get_text(strip=True)):
            return urljoin(ROOT, a["href"])
    return None


def find_notices(today=None):
    roc = year.current_roc_year()
    # ① 入口 → 「<roc>年度…SBIR專區」
    l2 = _find_link(http.get(ENTRY_URL).text, lambda t: f"{roc}年度" in t and "SBIR" in t)
    if not l2:
        return []
    # ② 年度專區 → 「…SBIR申請須知」公告（詳情頁）
    l3 = _find_link(http.get(l2).text, lambda t: "SBIR" in t and "申請須知" in t)
    if not l3:
        return []
    # ③ 詳情頁 → 檔名＝連結文字 → 通用掃法 + 兩把篩子
    return notice.pick_notices(notice.links_from(http.get(l3).text, ROOT), today=today)
