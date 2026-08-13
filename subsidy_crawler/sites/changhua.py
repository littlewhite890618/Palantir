# -*- coding: utf-8 -*-
"""
sites/changhua.py — 彰化縣 adapter【樣板②：requests + 二層導航】。

關鍵發現：service01_con.aspx（topsn=）是「內容頁」，各年度各自一個 data_id，
彼此沒有連結；但 service01_list.aspx（cate_id=，同一個編號）是「列表頁」，
會列出這個分類底下所有內容（含每一年的「<roc>年度彰化縣SBIR計畫」），
data_id 雖然逐年變動、無法預測，但可以從這個列表頁「當年度找到」，不用寫死。
  ① 列表頁 → 找「<roc>年度…SBIR」連結 → 拿到當年度的 data_id 詳情頁
  ② 詳情頁 → 連結文字本身就是檔名（如「下載115年作業要點及申請須知（519.00KB）」）
     → links_from + pick_notices
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, notice, year

DEPARTMENT = "彰化縣"
ROOT = "https://www.chcg.gov.tw/DTO/greenenergy/06service/"
HUB_URL = "https://www.chcg.gov.tw/DTO/greenenergy/06service/service01_list.aspx?cate_id=4593"


def _find_link(html_bytes, text_ok):
    soup = BeautifulSoup(html_bytes.decode("utf-8", "replace"), "lxml")
    for a in soup.find_all("a", href=True):
        if text_ok(a.get_text(strip=True)):
            return urljoin(ROOT, a["href"])
    return None


def find_notices(today=None):
    roc = year.current_roc_year()
    detail_url = _find_link(http.get(HUB_URL).content,
                            lambda t: f"{roc}年度" in t and "SBIR" in t)
    if not detail_url:
        return []
    resp = http.get(detail_url)
    candidates = notice.links_from(resp.content.decode("utf-8", "replace"), ROOT)
    return notice.pick_notices(candidates, today=today)
