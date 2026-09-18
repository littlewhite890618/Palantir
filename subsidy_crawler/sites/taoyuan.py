# -*- coding: utf-8 -*-
"""
sites/taoyuan.py — 桃園市 adapter【樣板②：requests，單頁多筆】。

地方型 SBIR 須知抓「投資桃園」入口頁（invest.tycg.gov.tw/cp.aspx?n=848）：這是**穩定頁面**
（頁 ID 固定、每年把當年度須知放上去），錨點文字就是檔名（如「115年SBIR申請須知.pdf」），
連結指向 ws.tycg.gov.tw 的真 PDF。篩「錨點文字含申請須知 + 當年度」即可，逐年自動跟上。
（原來源 taoyuan-sbir.tw/download 的 SBIR 須知下載會回舊版 .doc/OLE、管線不支援，已移除。）

另外抓經發局 edb（edb.tycg.gov.tw，ASP.NET WebForms）：最新消息預設列表是一般市政新聞，
補助公告要用站上搜尋器才撈得到。搜「公告」（postback：action 帶 &Create=1、按鈕值
「送出查詢」、需回填 __VIEWSTATE）→ 取當年度(115)結果 → 逐筆進子頁，抓附件 title 含
「申請須知」的檔（附件連結文字是「pdf(大小)」，真檔名在 title；下載走 ws.tycg.gov.tw/Download.ashx）。
"""
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, year

DEPARTMENT = "桃園市"

INVEST_URL = "https://invest.tycg.gov.tw/cp.aspx?n=848"   # 投資桃園·地方型SBIR（穩定頁，逐年換檔）

EDB_ROOT = "https://edb.tycg.gov.tw/"
EDB_LIST = EDB_ROOT + "News.aspx?n=3749&sms=9954"
EDB_SEARCH = EDB_ROOT + "News.aspx?n=3749&sms=9954&Create=1"   # 表單 action（postback）
EDB_KEYWORD = "公告"


def _edb_search(keyword):
    """ASP.NET postback 搜尋：回填 __VIEWSTATE + 關鍵字送出，回搜尋結果頁 HTML。"""
    soup = BeautifulSoup(http.get(EDB_LIST).content, "lxml")

    def v(elem_id):
        e = soup.select_one("#" + elem_id)
        return e.get("value", "") if e else ""

    resp = http.post(EDB_SEARCH, data={
        "__VIEWSTATE": v("__VIEWSTATE"),
        "__VIEWSTATEGENERATOR": v("__VIEWSTATEGENERATOR"),
        "__VIEWSTATEENCRYPTED": "",
        "jNewsModule_field_SDate_1": "",
        "jNewsModule_field_EDate_1": "",
        "jNewsModule_field_2": keyword,        # 關鍵字欄
        "jNewsModule_BtnSend": "送出查詢",       # 按鈕真值
    })
    return resp.content


def _edb_notices(today=None):
    """edb：搜「公告」→ 當年度(115)結果 → 進子頁抓 title 含「申請須知」的附件。"""
    roc = str(year.current_roc_year())
    soup = BeautifulSoup(_edb_search(EDB_KEYWORD), "lxml")
    sub_urls = list(dict.fromkeys(
        urljoin(EDB_ROOT, a["href"]) for a in soup.find_all("a", href=True)
        if "News_Content" in a["href"] and roc in a.get_text()))
    out, seen = [], set()
    for su in sub_urls:
        s2 = BeautifulSoup(http.get(su).content, "lxml")
        for a in s2.find_all("a", href=True):
            ti = a.get("title", "")
            if "申請須知" in ti and "Download" in a["href"]:
                name = re.sub(r"\s*\(另開新視窗\)\s*$", "", ti).strip()
                url = urljoin(EDB_ROOT, a["href"])
                if url not in seen:
                    seen.add(url)
                    out.append((name, url))
    return out


def _invest_notices(today=None):
    """投資桃園·地方型 SBIR 頁（cp.aspx?n=848）：錨點文字含『申請須知』＋當年度 → 取其 PDF 連結。
    頁 ID 固定、逐年換檔，錨點文字即檔名（如『115年SBIR申請須知.pdf』），連結指向 ws.tycg.gov.tw 真 PDF。"""
    soup = BeautifulSoup(http.get(INVEST_URL).content, "lxml")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        name = a.get_text(strip=True)
        if not name:
            continue
        if year.looks_like_notice(name) and year.has_current_year(name, today):
            url = urljoin(INVEST_URL, a["href"])
            if url not in seen:
                seen.add(url)
                name = re.sub(r"\s*\(另開新視窗\)\s*$", "", name).strip()
                out.append((name, url))
    return out


def find_notices(today=None):
    out = []
    out.extend(_invest_notices(today=today))   # 投資桃園 cp.aspx?n=848（地方型 SBIR 須知，穩定頁）
    out.extend(_edb_notices(today=today))       # 經發局 edb 搜「公告」找申請須知
    return out
