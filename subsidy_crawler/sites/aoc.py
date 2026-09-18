# -*- coding: utf-8 -*-
"""
sites/aoc.py — 經濟部商業發展署 adapter【內建搜尋(POST) + 多筆詳情】。

跟產發署/中小企業署同款「中央站：多個不同補助計畫並存」。這站「訊息公告」
（publicList/2）有自己的篩選表單（POST 回原網址），欄位：
    keyword（關鍵字）、beginMonth/endMonth（西元年月範圍，如"2026-01"）、
    pageCount（只能是10/20/30，其他值會讓查詢失效）
用 keyword=須知類關鍵字（見 KEYWORDS）+ beginMonth=當年度1月 篩出當年度的須知類
公告，不用瀏覽器（純 requests 就不擋）。
※ 年度篩選交給伺服器端的 beginMonth（很多公告標題本身沒有年份字樣，
   不能靠標題篩年度，例如「提升商業服務業營運效能強化韌性計畫」整合型補助
   申請須知——沒有「115」但確實是當年度公告）。
※ beginMonth 故意從「前一年12月」起算、不是當年1月：政府機關常在前一年12月就
   公告隔年計畫（尤其是1月截止的案子），若從當年1月起算會整批漏掉這類公告
   （實例：showPublic/539「智慧雨林產業創生計畫-智慧商業服務領域示範案及主題案
   申請須知」公告發布日2025/12/03，115年1月20日截止，beginMonth=2026-01
   會直接把它排除在搜尋結果外）。
※ 關鍵字不只「申請須知」：少數計畫標題用別的命名（品牌價值計畫叫「輔導徵選須知」），
   在 KEYWORDS 逐一補上、逐關鍵字各自搜一輪再合併去重（見 _search）。
※ 重要：paginationPage 是「從 0 開始算」（0=第1頁，1=第2頁…），一開始
   誤用 "1" 當第一頁，結果整個跳過真正的第一頁（18筆全部漏掉，只剩第二
   頁的7筆）。回應頁面本身有分頁按鈕（class="page-item"，其中一個帶
   active）可以核對目前在第幾頁；「下一頁」按鈕若帶 disabled 代表沒有下一頁了。
流程：
  ① 從 paginationPage=0 開始，逐頁 POST 搜尋，直到某頁抓不到任何結果為止
  ② 詳情頁 → 附件連結（/showPublicAttach/ID）文字本身就是完整檔名
     → looks_like_notice 篩須知類
"""
from datetime import date
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import http, year, render

DEPARTMENT = "經濟部商業發展署"
ROOT = "https://www.aoc.gov.tw/"
LIST_URL = "https://www.aoc.gov.tw/publicList/2"
# 站內搜尋用的關鍵字（公告標題含這些字才會被伺服器回傳）。多數計畫標題叫「申請須知」，
# 但少數用別的命名（例如品牌價值計畫叫「輔導徵選須知」），逐一補進來精準撈回，
# 不放寬成「須知」是因為那會混進一堆甄選/競賽公告。
KEYWORDS = ["申請須知", "輔導徵選須知"]
_MAX_PAGES = 20   # 安全上限，避免萬一停止條件失效造成無窮迴圈

# 台北市廣告代理商業同業公會 taaa（純 requests + render）：新聞快訊有分頁（?p=N），
# 每則 <li class="base-item"> 有 .date-cont（發布日）跟 .topic-cont a（詳情連結），
# 逐頁篩當年度、某頁全部過舊即停（同 eii.py 的「按日期新到舊排序」假設）。
# 文章子頁裡「申請須知」是段落裡連結*前面*的文字，不在 <a> 標籤本身（例如
# 「申請須知： <a>https://reurl.cc/xxx</a>」），要看父層 <p> 的文字才篩得到，
# 光比對 <a> 自己的文字會漏掉（之前就是這樣漏了115年度廣告設計優化輔導那筆）。
# 連結常是短網址，最終導到 Google Drive 共用資料夾（不是直接 PDF），要 render
# 該頁抓檔案清單，做法同 sites/yilan.py 的 Drive 資料夾解析。
TAAA_ROOT = "https://www.taaa.org.tw/"
TAAA_LIST = TAAA_ROOT + "news/news"
_TAAA_MAX_PAGES = 20

# smebiz.org.tw（財團法人資訊工業策進會代管，「商業服務業智慧轉型專區」檔案下載區）：
# 提升商業服務業營運效能強化韌性計畫（單店導入/多店升級/整合型補助）等計畫在 aoc.gov.tw 官網
# 常被拆成好幾個「附件N-M」片段檔各自收錄（見 extract_fields.py 的 _is_attachment_fragment），
# 這個頁面提供官方自己合併好的單一完整PDF，用來補回那幾個計畫的乾淨版本。已查證這個頁面會
# 逐年更新（同時有「115年5月修正版」「第二梯次收件」等多版本標記並存，不是靜態頁面）。
SMEBIZ_ROOT = "https://www.smebiz.org.tw/"
SMEBIZ_DOWNLOAD = SMEBIZ_ROOT + "download.php"


def _search_page(keyword, page, today=None):
    """POST 搜尋「keyword」+ 當年度起，抓「單一頁」→ 回傳 [(公告標題, 詳情網址), ...]。"""
    d = today or date.today()
    begin = date(d.year - 1, 12, 1)   # 往前挪一個月，涵蓋前一年12月公告的隔年計畫
    resp = http.post(LIST_URL, data={
        "keyword": keyword,
        "beginMonth": f"{begin.year}-{begin.month:02d}",
        "endMonth": "",
        "pageCount": "30",           # 只能是 10/20/30
        "paginationPage": str(page),  # 從 0 開始算
    })
    soup = BeautifulSoup(resp.content.decode("utf-8", "replace"), "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/showPublic/" not in href:
            continue
        title = a.get_text(strip=True)
        if not title:
            continue
        out.append((title, urljoin(ROOT, href)))
    return out


def _search(today=None):
    """逐關鍵字、逐頁抓（paginationPage 從 0 起算），合併並以詳情網址去重。"""
    out, seen = [], set()
    for keyword in KEYWORDS:
        for page in range(_MAX_PAGES):
            page_results = _search_page(keyword, page, today=today)
            if not page_results:
                break   # 這個關鍵字翻完了，換下一個關鍵字
            for title, url in page_results:
                if url not in seen:
                    seen.add(url)
                    out.append((title, url))
    return out


def _notice_files(html):
    """詳情頁附件（/showPublicAttach/ID）→ 連結文字本身就是完整檔名 → 篩須知類。"""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        if "/showPublicAttach/" not in a["href"]:
            continue
        name = a.get_text(strip=True) or a.get("title", "")
        if year.looks_like_notice(name):
            out.append((name, urljoin(ROOT, a["href"])))
    return out


def _drive_folder_notices(html, today=None):
    """Google Drive 共用資料夾頁 → 篩「當年度＋須知類」檔（同 sites/yilan.py 的解析法：
    data-id 是檔案id、真檔名在 aria-label，兩者分開放要各自讀取再配對）。"""
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set()
    for el in soup.find_all(attrs={"data-id": True}):
        fid = el["data-id"]
        aria = el.get("aria-label", "")
        if not aria:
            child = el.find(attrs={"aria-label": True})
            aria = child.get("aria-label", "") if child else ""
        name = aria.split(" ", 1)[0] if aria else ""
        if not name or fid in seen:
            continue
        if year.has_current_year(name, today) and year.looks_like_notice(name):
            seen.add(fid)
            out.append((name, f"https://drive.google.com/uc?export=download&id={fid}"))
    return out


def _taaa_notices(today=None):
    """taaa 新聞快訊 → 逐頁（li.base-item 的 .date-cont 篩當年度，某頁全過舊即停）→
    當年度文章子頁 → 找「申請須知」段落裡的連結（常是短網址、最終導到 Google Drive
    共用資料夾）→ render 該資料夾頁抓當年度須知檔。"""
    out = []
    for page in range(1, _TAAA_MAX_PAGES + 1):
        soup = BeautifulSoup(http.get(f"{TAAA_LIST}?p={page}").content, "lxml")
        items = soup.select("li.base-item")
        if not items:
            break
        page_has_current = False
        for li in items:
            date_el = li.select_one(".date-cont")
            a = li.select_one(".topic-cont a[href]")
            if date_el is None or a is None:
                continue
            if not year.is_recent_western_date(date_el.get_text(strip=True), today=today):
                continue
            page_has_current = True
            art_url = urljoin(TAAA_ROOT, a["href"])
            s2 = BeautifulSoup(http.get(art_url).content, "lxml")
            for link in s2.find_all("a", href=True):
                parent_text = link.parent.get_text(strip=True) if link.parent else ""
                if "申請須知" not in parent_text:
                    continue
                drive_url = urljoin(art_url, link["href"])
                try:
                    drive_html = render.render_html(drive_url)
                except Exception:
                    continue
                out.extend(_drive_folder_notices(drive_html, today=today))
        if not page_has_current:
            break   # 這頁已無當年度公告（按日期新到舊排，之後只會更舊）
    return out


def _smebiz_notices():
    """smebiz.org.tw/download.php：每筆記錄(row)通常掛好幾個檔案，f=1固定是官方合併好的完整
    PDF（須知本體+前幾號附件），f=2/f=3是另外拆出來的附件檔——只取PDF那個（用icon圖示判斷，
    比用URL的f=數字更穩，避免像aoc.gov.tw那樣把單一份須知拆成好幾筆碎片檔各自收錄）。不套用
    looks_like_notice篩選（這個頁面本身就是專屬檔案下載區，title都已含「申請須知」）、不套用
    年度篩選（很多標題本身沒有年份字樣，靠標題篩年度會誤刪，同本檔其他函式的既有理由）。
    包try/except：這是附加來源，網站打不開或改版導致抓不到東西時，只印警告、回傳空清單，
    不能讓這個來源的問題連帶讓aoc.gov.tw主要來源（同一個find_notices()呼叫）也爬不到。"""
    try:
        html = http.get(SMEBIZ_DOWNLOAD).content.decode("utf-8", "replace")
    except Exception as ex:
        print(f"[smebiz.org.tw] 抓取失敗，略過這個來源：{type(ex).__name__}: {ex}")
        return []
    soup = BeautifulSoup(html, "lxml")
    out = []
    for row in soup.select(".download-table-tr"):
        title_el = row.select_one(".title")
        if not title_el:
            continue
        name = title_el.get_text(strip=True)
        pdf_a = next((a for a in row.find_all("a", href=True)
                      if a.find("img") and "icon-pdf" in (a.find("img").get("src") or "")), None)
        if not pdf_a:
            continue
        out.append((name, urljoin(SMEBIZ_ROOT, pdf_a["href"])))
    if not out:
        print("[smebiz.org.tw] 抓到0筆，網頁結構可能改版了，需要人工檢查")
    return out


def find_notices(today=None):
    out = []
    for _title, durl in _search(today=today):
        detail_html = http.get(durl).content.decode("utf-8", "replace")
        out.extend(_notice_files(detail_html))
    out.extend(_taaa_notices(today=today))   # taaa 新聞快訊（目前無申請須知，保留邏輯）
    out.extend(_smebiz_notices())
    return out
