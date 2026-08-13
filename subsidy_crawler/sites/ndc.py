# -*- coding: utf-8 -*-
"""
sites/ndc.py — 國家發展委員會 adapter【Cloudflare + render + 列表→多筆詳情】。

國發會主站有 Cloudflare（用反偵測 selenium 有頭瀏覽器+熱身過關）。補助案放在
「補助資訊」專頁（即最新資訊的「單元＝補助資訊」內容，但這頁只列補助資訊，較穩定）。
流程：
  ① render 補助資訊列表 → 表格(#gvIndex) 每列(單元/標題/民國年日期)
     → 篩「當年度 + 受理申請」的公告（那種才附作業要點/申請須知）
  ② render 每個詳情頁 → 附件是 Download.ashx?u=..&n=<base64檔名> → 解出檔名
     → looks_like_notice 篩須知/作業要點類，申請須知優先
※ 檔案伺服器 ws.ndc.gov.tw 沒有 Cloudflare，下載用一般 http.download 即可（不設 NEEDS_BROWSER_DOWNLOAD）。
"""
import base64
from urllib.parse import urljoin, urlparse, parse_qs, unquote
from bs4 import BeautifulSoup

from ..common import render, year

DEPARTMENT = "國家發展委員會"
ROOT = "https://www.ndc.gov.tw/"
LIST_URL = "https://www.ndc.gov.tw/News.aspx?n=17E5A1FA758E2C0E&sms=2D58DD7349ACB619"
WARMUP = "https://www.ndc.gov.tw/"


def _list_detail_links(html, today=None):
    """補助資訊列表 → 篩「當年度 + 受理申請」的詳情頁網址。"""
    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("#ContentPlaceHolder1_gvIndex")
    out = []
    if table is None:
        return out
    for tr in table.find_all("tr"):
        a = tr.find("a", href=True)
        if a is None:
            continue
        title = a.get_text(strip=True)
        # 只要「受理申請中」的當年度公告——結果名單/審查結果那些沒有申請須知
        if "受理申請" not in title:
            continue
        if not year.has_current_year(title, today):
            continue
        out.append(urljoin(ROOT, a["href"]))
    return out


def _decode_name(href):
    """Download.ashx?...&n=<base64> → 解出原始檔名（檔名沒放在連結文字，只放格式標籤）。"""
    n = parse_qs(urlparse(href).query).get("n", [""])[0]
    try:
        return base64.b64decode(unquote(n)).decode("utf-8", "replace")
    except Exception:
        return ""


def _notice_files(html):
    """詳情頁附件 → 解檔名 → 只要檔名含「申請須知」的（不要作業要點類備案）。"""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "Download.ashx" not in href:
            continue
        name = _decode_name(href)
        if "申請須知" in name:
            out.append((name, urljoin(ROOT, href)))
    return out



def find_notices(today=None):
    list_html = render.selenium_fetch(LIST_URL, warmup=WARMUP, wait=15, headless=False)
    detail_urls = _list_detail_links(list_html, today=today)
    out = []
    for durl in detail_urls:
        html = render.selenium_fetch(durl, warmup=WARMUP, wait=12, headless=False)
        out.extend(_notice_files(html))
    return out
