# -*- coding: utf-8 -*-
"""
sites/lienchiang.py — 連江縣 adapter【樣板②變體：requests + 站內搜尋（POST）】。

連江縣府站沒有專屬 SBIR 列表頁，用全站搜尋（POST 表單，欄位 qstr1）搜「地方型SBIR」，
結果頁列出跨年度所有相關公告/檔案，用 links_from + pick_notices 篩出當年度須知。
搜尋結果的連結文字格式是「開新視窗,下載<檔名>」，需去掉固定前綴才是乾淨檔名。
"""
from ..common import http, notice

DEPARTMENT = "連江縣"
SEARCH_URL = "https://www.matsu.gov.tw/chhtml/search/371030000A/124"
KEYWORD = "地方型SBIR"
_TITLE_PREFIX = "開新視窗,下載"


def _candidates(html):
    cands = notice.links_from(html, SEARCH_URL)
    out = []
    for name, url in cands:
        if name.startswith(_TITLE_PREFIX):          # 去掉「開新視窗,下載」前綴，留乾淨檔名
            name = name[len(_TITLE_PREFIX):]
        out.append((name, url))
    return out


def find_notices(today=None):
    resp = http.post(SEARCH_URL, data={"qstr1": KEYWORD, "sitesearch": ""})
    return notice.pick_notices(_candidates(resp.text), today=today)
