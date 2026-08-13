# -*- coding: utf-8 -*-
"""
sites/eii.py — 經濟部產業發展署 adapter【樣板②：requests + 列表→詳情，多筆】。

跟地方 SBIR 站不同：中央站同時有「多個不同補助計畫」並存（不是一年一份）。
列表頁有分頁（news_list.php?m=1&page=N，目前約8頁），且按日期新到舊排序——
逐頁掃描，直到某頁篩不出任何「當年度」公告為止（代表之後只會更舊，不用再往下翻）。
流程：
  ① 逐頁列表 → 每列 <tr> 有 <td class="date"> 公告發布日（西元格式，如 2026/07/29）
     → 只留「當年度」公告的詳情連結
  ② 逐一進詳情頁 → 用 looks_like_notice 篩出「申請須知」類附件（不篩年度——
     每個計畫是獨立案子，不是同一份逐年更新，各自的須知都要收）
"""
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, year

DEPARTMENT = "經濟部產業發展署"
ROOT = "https://eii.nat.gov.tw/tiip/"
LIST_URL = "https://eii.nat.gov.tw/tiip/news_list.php?m=1"   # 只取主題式公告


def _list_detail_links(html, today=None):
    """列表頁 → 抓出「當年度公告」的詳情連結（依每列 <td class="date"> 篩選）。"""
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set()
    for row in soup.select("tr"):
        date_td = row.select_one("td.date")
        a = row.select_one("a[href]")
        if date_td is None or a is None:
            continue
        if not year.is_recent_western_date(date_td.get_text(strip=True), today=today):
            continue
        href = a["href"]
        if "news_page.php" in href:
            url = urljoin(ROOT, href)
            if url not in seen:
                seen.add(url)
                out.append(url)
    return out


def _notice_files(html):
    """詳情頁 → 篩出「申請須知」類附件（不篩年度，每個計畫都是獨立案子）。

    每個計畫常同時放「公告(含公告事項)」和「申請須知」兩份附件，兩者
    都含 NOTICE_KEYWORDS 裡的關鍵字（「公告事項」也是關鍵字之一）。但
    申請須知是我們最優先要的，同一計畫有申請須知就不必再收公告——
    所以候選裡只要出現「申請須知」字樣的，就只留那些，公告類的捨棄；
    真的沒有「申請須知」命名的計畫（例如只叫「作業要點」），才保留全部候選當備案。
    """
    soup = BeautifulSoup(html, "lxml")
    candidates = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not any(href.lower().endswith(e) for e in (".pdf", ".docx", ".doc", ".zip", ".odt")):
            continue
        name = a.get_text(strip=True) or a.get("title", "")
        if year.looks_like_notice(name):
            candidates.append((name, urljoin(ROOT, href)))
    priority = [c for c in candidates if "申請須知" in c[0]]
    return priority if priority else candidates


_MAX_PAGES = 20   # 安全上限，避免萬一停止條件失效造成無窮迴圈


def find_notices(today=None):
    out = []
    for page in range(1, _MAX_PAGES + 1):
        list_html = http.get(f"{LIST_URL}&page={page}").text
        soup = BeautifulSoup(list_html, "lxml")
        if soup.select_one("td.date") is None:
            break   # 沒有更多列了（超過最後一頁）
        detail_urls = _list_detail_links(list_html, today=today)
        if not detail_urls:
            break   # 這頁已經沒有當年度公告（按日期新到舊排，之後只會更舊）
        for durl in detail_urls:
            out.extend(_notice_files(http.get(durl).text))
    return out
