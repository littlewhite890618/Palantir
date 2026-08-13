# -*- coding: utf-8 -*-
"""
sites/chiayi_county.py — 嘉義縣 adapter【樣板②：requests + 二層導航】。

  ① 列表頁 → 找「<roc>年…SBIR」的公告連結（每年固定會有一則「<roc>年嘉義縣
     地方型SBIR計畫簡介」，人工確認過會逐年更新）
  ② 詳情頁附件 → 檔名在 title（連結文字只是格式+大小，如「pdf(272.56 KB)」）
     → looks_like_notice 篩須知類
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, year

DEPARTMENT = "嘉義縣"
ROOT = "https://economic.cyhg.gov.tw/"
LIST_URL = "https://economic.cyhg.gov.tw/News.aspx?n=1860&sms=15202"


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
        if year.looks_like_notice(name):
            out.append((name, urljoin(ROOT, a["href"])))
    return out


def find_notices(today=None):
    roc = year.current_roc_year()
    list_soup = BeautifulSoup(http.get(LIST_URL).content, "lxml")
    detail_url = _find_link(list_soup, lambda t: f"{roc}年" in t and "SBIR" in t)
    if not detail_url:
        return []
    detail_soup = BeautifulSoup(http.get(detail_url).content, "lxml")
    return _notice_files(detail_soup)
