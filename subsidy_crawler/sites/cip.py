# -*- coding: utf-8 -*-
"""
sites/cip.py — 原住民族委員會（cip.gov.tw）adapter【樣板②：requests，列表→子頁】。

「經濟發展」公告分類（data-list/DD56092E0C92EC1F）列出各原住民族補助計畫公告；每筆公告
是一個 <hash>-info.html 子頁，附件為 T-<id>.pdf（連結文字＝檔名）。逐筆進子頁，抓檔名
含「申請須知」的 PDF。

※ 這頁有分頁（JS doPage(N) 送出隱藏表單，實際等同 index.html?...&currentPage=N），
   原本沒處理只抓第1頁（第1頁多是審查結果/核定公告，申請須知都在第2頁），漏掉一整批
   115年度申請須知（產業推升計畫、農產運銷加值輔導、創新成長、創業共好、特色農業升級…）。
※ 年度篩選要看「文章列表的標題文字」，不能看附件檔名——附件檔名常常不帶年份（例如
   「產業推升計畫-申請須知.pdf」完全沒寫115），但同一篇舊文章（114年度）的附件檔名
   反而會明確標「114年度」。所以在進子頁「之前」就先用列表上的標題文字判斷年度，
   對到當年度的文章才進去抓附件，不當年度的整篇跳過。
※ 分頁停止條件：這頁「一篇當年度文章都沒有」就整批停止翻頁（同 eii.py／taaa／tmti
   的假設：按日期新到舊排序，某頁全過舊代表之後只會更舊，不用再往下翻）。
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, year

DEPARTMENT = "原住民族委員會"
ROOT = "https://www.cip.gov.tw/"
LIST_URL = ROOT + "zh-tw/news/data-list/DD56092E0C92EC1F/index.html?cumid=DD56092E0C92EC1F"
_MAX_PAGES = 20


def find_notices(today=None):
    out, seen_url, seen_info = [], set(), set()
    for page in range(1, _MAX_PAGES + 1):
        soup = BeautifulSoup(http.get(f"{LIST_URL}&currentPage={page}").content, "lxml")
        infos = list(dict.fromkeys(
            (urljoin(LIST_URL, a["href"]), a.get_text(strip=True))
            for a in soup.find_all("a", href=True) if "-info.html" in a["href"]))
        new_infos = [(u, t) for u, t in infos if u not in seen_info]
        seen_info.update(u for u, _ in new_infos)
        page_has_current = False
        for u, list_text in new_infos:
            if not year.has_current_year(list_text, today=today):
                continue   # 文章標題不是當年度，整篇跳過，不進子頁
            page_has_current = True
            s2 = BeautifulSoup(http.get(u).content, "lxml")
            for a in s2.find_all("a", href=True):
                name = a.get_text(strip=True) or a.get("title", "")
                if "申請須知" in name and ".pdf" in a["href"].lower():
                    url = urljoin(u, a["href"])
                    if url not in seen_url:
                        seen_url.add(url)
                        out.append((name, url))
        if not page_has_current:
            break   # 這頁已無當年度公告（按日期新到舊排，之後只會更舊）
    return out
