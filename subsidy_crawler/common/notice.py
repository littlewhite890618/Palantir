# -*- coding: utf-8 -*-
"""
common/notice.py — 從頁面的檔案清單中，挑出「當年度的須知類」檔案。

分工：
- 各站 adapter（sites/*.py）負責「從該站 HTML 解析出候選檔案清單」——每站結構不同。
- 這裡提供「共用」工具：
    absolute()     把相對網址補成完整網址
    links_from()   通用掃法：抓頁面所有 <a> 的（文字, 網址）
    pick_notices() 用兩把篩子（年度＋須知）從候選清單挑出目標
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from . import year


def absolute(base_url, href):
    """把相對連結（如 index.php?...）補成完整網址。"""
    return urljoin(base_url, href)


def links_from(html, base_url):
    """通用：掃出頁面所有 <a>，回傳 [(連結文字, 絕對網址), ...]。
    適用於「檔名就是連結文字」的站；檔名另放它處的站（如金門）由 adapter 自行解析。"""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        # 連結文字為主；有些站文字空、檔名放在 title 屬性（如南投），就退而用 title。
        text = a.get_text(strip=True) or a.get("title", "").strip()
        out.append((text, absolute(base_url, a["href"])))
    return out   #回傳[(文字, 網址)]


def pick_notices(candidates, today=None):
    """從候選清單挑出「當年度 且 須知類」的檔案。
    candidates: [(檔名, 網址), ...] → 回傳同格式的過濾結果。"""
    result = []
    for name, url in candidates:
        if year.has_current_year(name, today) and year.looks_like_notice(name):
            result.append((name, url))
    return result
