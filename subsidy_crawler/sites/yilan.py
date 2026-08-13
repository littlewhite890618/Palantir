# -*- coding: utf-8 -*-
"""
sites/yilan.py — 宜蘭縣 adapter【樣板③：render，Google Sites + Google Drive】。

宜蘭用 Google Sites 做資料下載區（SPA，需 render），
真正的申請須知檔又放在「Google Drive 資料夾」連結裡面（要再 render 一層 Drive 頁）：
    ① render 入口頁 → 找「<roc>年度計畫申請資料」連到的 Drive 資料夾網址
    ② render 該 Drive 資料夾 → 用 data-id + aria-label 抓出「申請須知」檔的 (檔名, 檔案id)
    ③ 用 Drive 下載連結 uc?export=download&id=<檔案id> 下載（一般 requests 可直接下載，不用瀏覽器）
"""
import re
from bs4 import BeautifulSoup

from ..common import http, render, year

DEPARTMENT = "宜蘭縣"
ENTRY_URL = "https://sites.google.com/view/yilansbir/資料下載區"


def _drive_folder_url(html, today=None):
    """從入口頁找「<roc>年度計畫申請資料」連到的 Google Drive 資料夾網址。"""
    roc = year.current_roc_year()
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        t = a.get_text(strip=True)
        if f"{roc}年度" in t and "申請" in t and "drive.google.com/drive/folders" in a["href"]:
            return a["href"]
    return None


def _files_in_drive_folder(html, today=None):
    """從 Drive 資料夾頁抓「檔名含須知類關鍵字」的 (檔名, 下載網址)。
    Drive 把「data-id」和「aria-label（真檔名）」分開放，需分別讀取再配對。"""
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set() #set()自動去重，避免同一檔案出現多個 <div> 造成重複抓取
    for el in soup.find_all(attrs={"data-id": True}):
        fid = el["data-id"]
        aria = el.get("aria-label", "")
        if not aria:                                    # 檔名常在子元素的 aria-label
            child = el.find(attrs={"aria-label": True})
            aria = child.get("aria-label", "") if child else ""
        name = aria.split(" ", 1)[0] if aria else ""     # aria-label 例："xxx.docx Microsoft Word 已共用"
        if not name or fid in seen:
            continue
        if year.has_current_year(name, today) and year.looks_like_notice(name):
            seen.add(fid)
            out.append((name, f"https://drive.google.com/uc?export=download&id={fid}"))
    return out


def find_notices(today=None):
    """render 入口 → 找 Drive 資料夾 → render 資料夾 → 抓當年度申請須知。"""
    folder_url = _drive_folder_url(render.render_html(ENTRY_URL), today=today)
    if not folder_url:
        return []
    return _files_in_drive_folder(render.render_html(folder_url), today=today)
