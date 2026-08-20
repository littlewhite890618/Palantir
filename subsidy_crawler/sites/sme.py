# -*- coding: utf-8 -*-
"""
sites/sme.py — 經濟部中小及新創企業署 adapter【樣板②：requests + 列表→多筆詳情】。

同產發署：中央站同時有多個補助/計畫並存，不是一年一份。
列表頁有分頁（list-tw-2275?page=N，目前共3頁）——逐頁掃，直到某頁抓不到
任何詳情連結為止（代表已經翻完，沒有更多）。
  ① 業務消息列表（article-tw-2275-\\d+）→ 抓每頁全部詳情連結
  ② 詳情頁 div.fileDownloadBox 裡的附件 → 檔名在 <a title="檔名.pdf(另開新視窗)">
     → 篩出「申請須知」類（不篩年度）

另外抓 SBIR 官網（sbir.org.tw/sbir/dw_apply，SBIR＝小型企業創新研發計畫，承辦為中企署）：
申請階段下載頁把「115年SBIR申請須知.pdf」直接列出，連結文字就是帶年份的乾淨檔名。
純 requests 就抓得到；此頁固定、逐年換檔（只放當年度檔），用 has_current_year +
looks_like_notice 自動挑當年度那份，明年自動跟上 116，不必改網址。
"""
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, year

DEPARTMENT = "經濟部中小及新創企業署"
ROOT = "https://www.sme.gov.tw/"
LIST_URL_TMPL = "https://www.sme.gov.tw/list-tw-2275?page={page}"

SBIR_ROOT = "https://sbir.org.tw/"
SBIR_URL = "https://sbir.org.tw/sbir/dw_apply"   # SBIR 申請階段下載頁（固定、逐年換檔）
CROSS_URL = "https://sbir.org.tw/cross/download"   # 企業跨域研發補助 下載專區（同站、固定頁）

# 業務消息歷史區（list-tw-2814）：結構同 list-tw-2275（article-tw-2814 詳情頁、?page=N 分頁、
# 詳情頁 .fileDownloadBox 附件），但這是「歷史區」共約29頁、日期橫跨到 2025 以前的舊須知，
# 一定要篩年度：列表每筆標題結尾帶發布日（如「…申請須知2026-02-10」），用 is_recent_western_date
# 篩當年度，某頁全部過舊即停（策略A，按日期新到舊排序）。
HISTORY_LIST_TMPL = "https://www.sme.gov.tw/list-tw-2814?page={page}"
_HISTORY_DETAIL_RE = re.compile(r"article-tw-2814-\d+")

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


def _sbir_notices(today=None):
    """SBIR 申請階段下載頁 → 連結文字＝帶年份的檔名 → 篩「當年度＋須知類」。"""
    soup = BeautifulSoup(http.get(SBIR_URL).content, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        name = a.get_text(strip=True)
        if not name:
            continue
        if year.has_current_year(name, today) and year.looks_like_notice(name):
            out.append((name, urljoin(SBIR_ROOT, a["href"])))
    return out


def _cross_notices(today=None):
    """企業跨域研發補助 下載專區 → 連結文字＝帶年份的檔名 → 篩「當年度＋須知類」
    （同一頁混了懶人包/簡報/契約範本/作業手冊等大量附件，須知關鍵字自然把非須知濾掉）。"""
    soup = BeautifulSoup(http.get(CROSS_URL).content, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        name = a.get_text(strip=True)
        if not name:
            continue
        if year.has_current_year(name, today) and year.looks_like_notice(name):
            out.append((name, urljoin(SBIR_ROOT, a["href"])))
    return out


def _history_notices(today=None):
    """業務消息歷史區（list-tw-2814）→ 逐頁：列表每筆 <a> 文字含「標題＋發布日」，
    「標題含當年度(115) 或 發布日是當年度」即進詳情抓申請須知；某頁全過舊即停（策略A）。
    ※ 用「標題含115 或 日期2026」兩者其一，是因為政府常在前一年12月就公告隔年計畫
      （例：示範案及主題案申請須知發布日2025-12），只看發布日會漏掉這類。"""
    out, seen = [], set()
    for page in range(1, _MAX_PAGES + 1):
        soup = BeautifulSoup(http.get(HISTORY_LIST_TMPL.format(page=page)).content, "lxml")
        items = [a for a in soup.find_all("a", href=True) if _HISTORY_DETAIL_RE.search(a["href"])]
        if not items:
            break   # 沒有詳情連結了，翻完
        page_has_current = False
        for a in items:
            url = urljoin(ROOT, a["href"])
            if url in seen:
                continue
            text = a.get_text(strip=True)
            if not (year.has_current_year(text, today) or year.is_recent_western_date(text, today)):
                continue   # 標題非當年度、發布日也非當年度 → 跳過
            seen.add(url)
            page_has_current = True
            out.extend(_notice_files(http.get(url).text))
        if not page_has_current:
            break   # 這頁已無當年度公告（按日期新到舊排，之後只會更舊）
    return out


def find_notices(today=None):
    out = []
    for page in range(1, _MAX_PAGES + 1):
        detail_urls = _list_detail_links(http.get(LIST_URL_TMPL.format(page=page)).text)
        if not detail_urls:
            break   # 這頁沒有任何詳情連結，代表已經翻完了
        for durl in detail_urls:
            out.extend(_notice_files(http.get(durl).text))
    out.extend(_sbir_notices(today=today))    # 再加 SBIR 官網當年度申請須知
    out.extend(_cross_notices(today=today))   # 企業跨域研發補助 下載專區
    out.extend(_history_notices(today=today))  # 業務消息歷史區 list-tw-2814
    return out
