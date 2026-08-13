# -*- coding: utf-8 -*-
"""
sites/sme.py — 經濟部中小及新創企業署 adapter【樣板②：requests + 列表→多筆詳情】。

同產發署：中央站同時有多個補助/計畫並存，不是一年一份。
列表頁有分頁（list-tw-2275?page=N，目前共3頁）——逐頁掃，直到某頁抓不到
任何詳情連結為止（代表已經翻完，沒有更多）。
  ① 業務消息列表（article-tw-2275-\\d+）→ 抓每頁全部詳情連結
  ② 詳情頁 div.fileDownloadBox 裡的附件 → 檔名在 <a title="檔名.pdf(另開新視窗)">
     → 篩出「申請須知」類（不篩年度）
"""
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, year

DEPARTMENT = "經濟部中小及新創企業署"
ROOT = "https://www.sme.gov.tw/"
LIST_URL_TMPL = "https://www.sme.gov.tw/list-tw-2275?page={page}"

_DETAIL_RE = re.compile(r"article-tw-2275-\d+")
_MAX_PAGES = 20   # 安全上限，避免萬一停止條件失效造成無窮迴圈


def _list_detail_links(html):
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if _DETAIL_RE.search(href):
            url = urljoin(ROOT, href)
            if url not in seen:
                seen.add(url)
                out.append(url)
    return out


def _clean_title(title):
    """title 格式："檔名.pdf(另開新視窗)" → 去掉尾巴的 "(另開新視窗)"。"""
    return re.sub(r"\(另開新視窗\)\s*$", "", title).strip()


def _notice_files(html):
    """詳情頁附件裡，申請須知優先——同一計畫若有申請須知，就不收其他公告類附件。"""
    soup = BeautifulSoup(html, "lxml")
    box = soup.select_one(".fileDownloadBox")
    if box is None:
        return []
    candidates = []
    for a in box.find_all("a", href=True):
        name = _clean_title(a.get("title", "")) or a.get_text(strip=True)
        if year.looks_like_notice(name):
            candidates.append((name, urljoin(ROOT, a["href"])))
    priority = [c for c in candidates if "申請須知" in c[0]]
    return priority if priority else candidates


def find_notices(today=None):
    out = []
    for page in range(1, _MAX_PAGES + 1):
        detail_urls = _list_detail_links(http.get(LIST_URL_TMPL.format(page=page)).text)
        if not detail_urls:
            break   # 這頁沒有任何詳情連結，代表已經翻完了
        for durl in detail_urls:
            out.extend(_notice_files(http.get(durl).text))
    return out
