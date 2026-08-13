# -*- coding: utf-8 -*-
"""
sites/miaoli.py — 苗栗縣 adapter【樣板②：requests + 二層導航】。

  ① 列表頁 → 找「公告受理<roc>年度…（地方型SBIR）申請」的公告連結
  ② 詳情頁附件 → 檔名在 title，格式是「[另開新視窗]檔名」，要去掉前綴
     → looks_like_notice 篩須知類
※ 這站直接把 bytes 丟給 BeautifulSoup 會被誤判編碼（可能 meta charset 宣告有誤），
   要先明確 .decode("utf-8") 成字串，再交給 BeautifulSoup，不能讓它自己猜。
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, year

DEPARTMENT = "苗栗縣"
ROOT = "https://www.miaoli.gov.tw/economic_development/"
LIST_URL = "https://www.miaoli.gov.tw/economic_development/News.aspx?n=9707&sms=14729"
_TITLE_PREFIX = "[另開新視窗]"


def _soup(resp):
    return BeautifulSoup(resp.content.decode("utf-8"), "lxml")


def _find_link(soup, text_ok):
    for a in soup.find_all("a", href=True):
        if text_ok(a.get_text(strip=True)):
            return urljoin(ROOT, a["href"])
    return None


def _notice_files(soup):
    out = []
    for a in soup.find_all("a", href=True):
        if "Download.ashx" not in a["href"]:
            continue
        name = a.get("title", "").strip()
        if name.startswith(_TITLE_PREFIX):
            name = name[len(_TITLE_PREFIX):]
        if year.looks_like_notice(name):
            out.append((name, urljoin(ROOT, a["href"])))
    return out


def find_notices(today=None):
    roc = year.current_roc_year()
    detail_url = _find_link(_soup(http.get(LIST_URL)),
                            lambda t: "受理" in t and f"{roc}年度" in t and "SBIR" in t)
    if not detail_url:
        return []
    return _notice_files(_soup(http.get(detail_url)))
