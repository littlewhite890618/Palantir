# -*- coding: utf-8 -*-
"""
sites/kaohsiung.py — 高雄市 adapter【樣板②：requests + 多層導航】。

高雄的檔案藏在三層下：資料下載 → 當年度高雄市SBIR → 計畫申請階段 → 檔案。
每層都是靜態頁 → 用 http.get（不用瀏覽器）；最底層「檔名＝連結文字」，用 links_from + pick_notices。
導航是「年度動態」：靠 current_roc_year() 找「115年度…SBIR」，明年自動找 116。

另外抓經發局 edbkcg（edbkcg.kcg.gov.tw，ASP.NET）：最新消息列表 GET 直接載出，取
標題含「公告」＋當年度(115)的主題 → 進子頁抓附件 title 含「補助計畫」的 PDF
（附件 title 是真檔名帶「[另開新視窗]」尾綴；每頁另有數個頁尾 boilerplate 附件，
因不含「補助計畫」自然被排除）。
"""
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, notice, year

DEPARTMENT = "高雄市"
ROOT = "https://kh-sbir.kcg.gov.tw/"
ENTRY_URL = "https://kh-sbir.kcg.gov.tw/Content_List.aspx?n=62FA45A4D23BD9AA"   # 資料下載

EDBKCG_ROOT = "https://edbkcg.kcg.gov.tw/"
EDBKCG_LIST = EDBKCG_ROOT + "News.aspx?n=9A7F03ABA05E4DEF&sms=BE8A73D3A0435784"


def _find_link(html, text_ok):
    """在 html 裡找第一個「連結文字通過 text_ok() 判斷」的 <a>，回傳絕對網址；找不到回 None。"""
    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        if text_ok(a.get_text(strip=True)):
            return urljoin(ROOT, a["href"])
    return None


def _edbkcg_notices(today=None):
    """經發局 edbkcg：列表取含「公告」＋當年度主題 → 子頁附件 title 含「補助計畫」的 PDF。"""
    roc = str(year.current_roc_year())
    soup = BeautifulSoup(http.get(EDBKCG_LIST).content, "lxml")
    subs = list(dict.fromkeys(
        urljoin(EDBKCG_ROOT, a["href"]) for a in soup.find_all("a", href=True)
        if "News_Content" in a["href"] and "公告" in a.get_text() and roc in a.get_text()))
    out, seen = [], set()
    for su in subs:
        s2 = BeautifulSoup(http.get(su).content, "lxml")
        for a in s2.find_all("a", href=True):
            ti = a.get("title", "")
            if "補助計畫" in ti and ("Download" in a["href"] or ".pdf" in a["href"].lower()):
                name = re.sub(r"\s*\[另開新視窗\]\s*$", "", ti).strip()
                url = urljoin(EDBKCG_ROOT, a["href"])
                if url not in seen:
                    seen.add(url)
                    out.append((name, url))
    return out


def find_notices(today=None):
    """三層導航：資料下載 → 當年度SBIR → 計畫申請階段 → 抓當年度須知；再加經發局 edbkcg。"""
    roc = year.current_roc_year()
    out = []
    # 第①層：資料下載頁 → 找「<roc>年度…SBIR」的連結
    l2 = _find_link(http.get(ENTRY_URL).text, lambda t: f"{roc}年度" in t and "SBIR" in t)
    if l2:
        # 第②層：該年度頁 → 找「計畫申請階段」的連結
        l3 = _find_link(http.get(l2).text, lambda t: "申請階段" in t)
        if l3:
            # 第③層：檔案頁 → 檔名＝連結文字 → 通用掃法 + 兩把篩子
            out.extend(notice.pick_notices(notice.links_from(http.get(l3).text, ROOT), today=today))
    out.extend(_edbkcg_notices(today=today))   # 經發局 edbkcg 補助計畫
    return out
