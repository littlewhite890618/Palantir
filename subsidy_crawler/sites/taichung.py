# -*- coding: utf-8 -*-
"""
sites/taichung.py — 臺中市 adapter【樣板②：requests + 三層導航】。

三層導航（皆靜態頁 http.get）：
  ① 入口頁（地方型SBIR專頁）→ 找「<roc>年度」連結
  ② 該年度頁 → 找「申請階段」連結（同層還有簽約/期中/結案階段，不要進去）
  ③ 申請階段頁 → 檔名＝連結文字（如「01-115年度-申請須知.pdf」）→ links_from + pick_notices
年度動態：靠 current_roc_year()，明年自動找 116年度。
※ 這頁還混了 YouTube 說明影片連結（標題也含「115年度…申請須知」），
   links_from 不看 href 是不是真的檔案，要自己過濾掉非檔案連結，避免誤收影片網址。
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, notice, year

DEPARTMENT = "臺中市"
ROOT = "https://www.economic.taichung.gov.tw/"
ENTRY_URL = "https://www.economic.taichung.gov.tw/16103/16153/16163/1717445/2764073"
_FILE_EXT = (".pdf", ".docx", ".doc", ".zip", ".odt", ".ods")


def _find_link(html, text_ok):
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        if text_ok(a.get_text(strip=True)):
            return urljoin(ROOT, a["href"])
    return None


def find_notices(today=None):
    roc = year.current_roc_year()
    l2 = _find_link(http.get(ENTRY_URL).text, lambda t: f"{roc}年度" in t)
    if not l2:
        return []
    l3 = _find_link(http.get(l2).text, lambda t: t == "申請階段")
    if not l3:
        return []
    candidates = notice.links_from(http.get(l3).text, ROOT)
    files_only = []
    for name, url in candidates:
        if name.lower().endswith(_FILE_EXT):
            files_only.append((name, url))
    return notice.pick_notices(files_only, today=today)
