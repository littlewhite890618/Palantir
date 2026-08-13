# -*- coding: utf-8 -*-
"""
sites/pingtung.py — 屏東縣 adapter【樣板②：requests + 導航】。

WordPress 站，slug 混亂（連結文字寫「115」但網址 slug 是「114」），所以靠「文字」導航：
  ① 首頁 → 找文字「<roc>年計畫文件下載」→ 該年度檔案頁
  ② 檔案頁 → 檔案在 wp-content/uploads，連結文字是「下載」，檔名在網址 → 取 href 檔名 → pick_notices
"""
from urllib.parse import urljoin, unquote
from bs4 import BeautifulSoup

from ..common import http, notice, year

DEPARTMENT = "屏東縣"
ROOT = "https://pthg-sbir.nptu.edu.tw/"

_FILE_EXT = (".pdf", ".docx", ".doc", ".zip", ".odt", ".ods")


def _find_link(html, text_ok):
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        if text_ok(a.get_text(strip=True)):
            return urljoin(ROOT, a["href"])
    return None


def _files(html):
    """檔名在網址最後一段（連結文字只是「下載」）。"""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/wp-content/uploads/" in href and href.lower().endswith(_FILE_EXT):#下載按鈕網址包含 wp-content/uploads，連結文字只是「下載」，檔名在網址最後一段
            name = unquote(href.rsplit("/", 1)[-1])
            out.append((name, urljoin(ROOT, href)))
    return out


def find_notices(today=None):
    roc = year.current_roc_year()
    l2 = _find_link(http.get(ROOT).text, lambda t: f"{roc}年計畫文件下載" in t)
    if not l2:
        return []
    return notice.pick_notices(_files(http.get(l2).text), today=today)
