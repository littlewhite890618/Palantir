# -*- coding: utf-8 -*-
"""
sites/ida.py — 經濟部產業發展署（IDA）adapter【樣板②：requests + 列表→詳情，多筆】。
（原檔名 eii.py，2026-08 改名為 ida.py；DEPARTMENT 仍為「經濟部產業發展署」。）

跟地方 SBIR 站不同：中央站同時有「多個不同補助計畫」並存（不是一年一份）。
列表頁有分頁（news_list.php?m=1&page=N，目前約8頁），且按日期新到舊排序——
逐頁掃描，直到某頁篩不出任何「當年度」公告為止（代表之後只會更舊，不用再往下翻）。
流程：
  ① 逐頁列表 → 每列 <tr> 有 <td class="date"> 公告發布日（西元格式，如 2026/07/29）
     → 只留「當年度」公告的詳情連結
  ② 逐一進詳情頁 → 用 looks_like_notice 篩出「申請須知」類附件（不篩年度——
     每個計畫是獨立案子，不是同一份逐年更新，各自的須知都要收）

另擴充 7 個來源（2026-08）：keid cloud（2計畫）、keid citd（2計畫）、nqa、assist、
tmti、tdri IDDI（互動render，今年115已截止暫回0）、c_id=99 下載頁（產業升級創新
平台輔導計畫3子計畫）。各來源細節見對應函式與常數上的註解。
"""
import re
from datetime import date
from urllib.parse import urljoin, unquote, parse_qs, urlparse
from bs4 import BeautifulSoup

from ..common import http, year, render

DEPARTMENT = "經濟部產業發展署"
ROOT = "https://eii.nat.gov.tw/tiip/"
LIST_URL = "https://eii.nat.gov.tw/tiip/news_list.php?m=1"   # 只取主題式公告

# 產發局 keid 兩系統（純 requests）：
# ① cloud「找補助」兩計畫詳情頁：PDF 是 GUID 檔名、名稱在 <a> 周邊文字，篩含「申請須知」。
# ② citdweb 兩計畫的「計畫申請」下載頁：download 連結名稱在旁邊，篩含「申請須知」＋當年度
#    （標籤帶公告日與年份，混多年度，只留 115/2026 那批）。
KEID_CLOUD = "https://keid.nat.gov.tw/cloud/Web/"
KEID_CLOUD_PROJECTS = [KEID_CLOUD + "project_description.aspx",   # 中小製造業接班傳承AI應用數位轉型
                       KEID_CLOUD + "project_description2.aspx"]  # 智慧機械-產業聚落供應鏈…AI應用
KEID_CITD = "https://keid.nat.gov.tw/citdweb/Web/"
KEID_CITD_APPLY = [KEID_CITD + "CITD_Download1.aspx",   # 協助傳統產業技術開發計畫 → 計畫申請
                   KEID_CITD + "RDBC_Download1.aspx"]   # 提升產業競爭力-研發轉型補助 → 計畫申請
# 國家品質獎/卓越經營 nqa（純 requests）：News 列表取當年度公告 → 進子頁抓連結文字含「申請須知」
# 的檔（實際多為 .docx，非 pdf）。
NQA_BASE = "https://keid.nat.gov.tw/nqa/Web/"
NQA_LIST = NQA_BASE + "News.aspx?TC=1"
_DOC_EXT = (".pdf", ".doc", ".docx", ".odt")
# 中衛/輔導 assist（「產業競爭力發展中心」，純 requests）：計畫申請快訊列表取當年度公告 →
# 進子頁抓「連結文字含申請須知」的附件（附件連結文字帶 pdf/docx 圖示前綴＋真檔名，如
# 「pdf115…申請須知…公告版.pdf」）。
# ※ 這頁有分頁（nowPage=N），原本沒處理只抓第1頁，漏掉第2頁一整批115年度公告
#   （包含「高齡科技產業普惠加值」「創新醫療產品市場准入」等）。超出實際頁數時網站
#   會重複顯示最後一頁，故用「這頁沒有新項目就停」判斷，不猜確切頁數。
ASSIST_BASE = "https://assist.nat.gov.tw/wSite/"
ASSIST_LIST = ASSIST_BASE + "lp?ctNode=232&mp=2"
_ASSIST_MAX_PAGES = 20
# 金屬中心 tmti（純 requests，多機關公告匯集站）：逐筆進 news_detail 子頁，抓附件
# （file_download.php?fname=…）真檔名含「申請須知」的。命中率低但逐筆硬找。
TMTI_ROOT = "https://www.tmti.org/"
TMTI_LIST = TMTI_ROOT + "news.php?tbl=org"
_TMTI_MAX_PAGES = 20   # 這站有分頁（?page=N），原本沒處理只抓第1頁，用日期篩當年度＋
                       # 某頁全過舊即停（同 eii.py 假設按日期新到舊排序）
# 設計研究院 IDDI 補助（SPA，需 render + 點「參考文件」分頁才展開下載）：
# ※ IDDI 逐年一期、申請期一過參考文件下載即下架。今年 115 已截止 → 回 0 筆；
#    程式已就緒，明年新一期「參考文件」按鈕重現時自動抓到含「申請須知」的 PDF。
TDRI_IDDI = "https://www.tdri.org.tw/zh-TW/design-resource/iddi"
# 產業升級創新平台輔導計畫「申請審查階段」下載頁（同站 eii.nat.gov.tw，純 requests、只1頁）：
# 連結文字本身就是「申請須知(產業高值/創新優化/新興育成)[PDF]」，直接篩含「申請須知」即可。
# 固定網址、內容持續更新到最新年度（實測曾是113年版，現已更新成115年6月版），不用篩年度。
C99_URL = ROOT + "downloadList.php?c_id=99"


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


def _label_near(a):
    """往上找最近一層「有文字」的祖先，回傳其文字（GUID/空文字連結靠這個取名稱）。"""
    node = a
    for _ in range(5):
        node = node.parent
        if node is None:
            break
        txt = node.get_text(" ", strip=True)
        if txt:
            return txt
    return ""


def _keid_cloud_notices():
    """keid cloud 兩計畫詳情頁 → PDF 連結周邊文字含「申請須知」的收下。"""
    out = []
    for u in KEID_CLOUD_PROJECTS:
        soup = BeautifulSoup(http.get(u).content, "lxml")
        for a in soup.find_all("a", href=True):
            if ".pdf" not in a["href"].lower():
                continue
            label = _label_near(a)
            if "申請須知" in label:
                out.append((label, urljoin(u, a["href"])))
    return out


def _keid_citd_label_is_current(label, today=None):
    """標籤開頭常是公告日「YYYY/MM/DD」，用它精準判斷當年度——不只看今年，
    也接受「前一年12月」（政府機關常在前一年12月就發布隔年計畫的最新版申請須知，
    例如 CITD 的『產品開發及研發聯盟』申請須知實際是 2025/12/30 發布、給115年度用，
    標籤本身完全沒有「115」字樣，若只看有沒有「115」會被誤判成舊版而濾掉）。
    標籤沒有日期可判斷時，才退回看有沒有「115」字樣。"""
    d = today or date.today()
    m = re.match(r"(\d{4})/(\d{1,2})/(\d{1,2})", label)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        return y == d.year or (y == d.year - 1 and mo == 12)
    return str(year.current_roc_year()) in label


def _keid_citd_notices(today=None):
    """keid citd 兩計畫「計畫申請」頁 → download 連結名稱含「申請須知」＋當年度。"""
    out = []
    for u in KEID_CITD_APPLY:
        soup = BeautifulSoup(http.get(u).content, "lxml")
        for a in soup.find_all("a", href=True):
            if "action=download" not in a["href"]:
                continue
            label = _label_near(a)
            if "申請須知" not in label:
                continue
            if not _keid_citd_label_is_current(label, today=today):
                continue
            name = re.sub(r"^\d{4}/\d{2}/\d{2}\s*", "", label)   # 去掉開頭公告日
            name = re.sub(r"\s+\d+$", "", name).strip()          # 去掉結尾下載次數
            out.append((name, urljoin(u, a["href"])))
    return out


def _nqa_notices(today=None):
    """nqa News 列表 → 當年度公告子頁 → 連結文字含「申請須知」的檔（多為 .docx）。"""
    roc = str(year.current_roc_year())
    soup = BeautifulSoup(http.get(NQA_LIST).content, "lxml")
    sub_urls = [urljoin(NQA_BASE, a["href"]) for a in soup.find_all("a", href=True)
                if "News_Content" in a["href"] and roc in a.get_text()]
    out, seen = [], set()
    for su in sub_urls:
        s2 = BeautifulSoup(http.get(su).content, "lxml")
        for a in s2.find_all("a", href=True):
            t = a.get_text(strip=True)
            if "申請須知" in t and a["href"].lower().endswith(_DOC_EXT):
                url = urljoin(NQA_BASE, a["href"])
                if url not in seen:
                    seen.add(url)
                    out.append((t, url))
    return out


def _assist_notices(today=None):
    """assist 計畫申請快訊 → 逐頁（nowPage=N，某頁沒有新項目就停）取當年度公告子頁 →
    附件連結文字含「申請須知」的收下。"""
    roc = str(year.current_roc_year())
    out, seen_url, seen_sub = [], set(), set()
    for page in range(1, _ASSIST_MAX_PAGES + 1):
        soup = BeautifulSoup(http.get(f"{ASSIST_LIST}&nowPage={page}&pagesize=15").content, "lxml")
        sub_urls = list(dict.fromkeys(
            urljoin(ASSIST_BASE, a["href"]) for a in soup.find_all("a", href=True)
            if "ct?xItem" in a["href"] and roc in a.get_text()))
        new_subs = [u for u in sub_urls if u not in seen_sub]
        if not new_subs:
            break   # 超出實際頁數，網站重複顯示最後一頁，沒有新項目就停
        seen_sub.update(new_subs)
        for su in new_subs:
            s2 = BeautifulSoup(http.get(su).content, "lxml")
            for a in s2.find_all("a", href=True):
                t = a.get_text(strip=True)
                if "申請須知" not in t:
                    continue
                if "DownloadFile" not in a["href"] and "file=" not in a["href"]:
                    continue
                name = re.sub(r"^(pdf|docx|doc|odt)", "", t).strip()   # 去掉圖示前綴
                url = urljoin(ASSIST_BASE, a["href"])
                if url not in seen_url:
                    seen_url.add(url)
                    out.append((name, url))
    return out


def _tmti_notices(today=None):
    """tmti news 列表 → 逐頁（li.news_List 的 .news_Date 篩當年度，某頁全過舊即停）→
    當年度文章子頁 → 附件真檔名（fname）含「申請須知」的收下。"""
    out, seen = [], set()
    for page in range(1, _TMTI_MAX_PAGES + 1):
        url = TMTI_LIST if page == 1 else f"{TMTI_LIST}&page={page}"
        soup = BeautifulSoup(http.get(url).content, "lxml")
        items = soup.select("li.news_List")
        if not items:
            break
        page_has_current = False
        for li in items:
            date_el = li.select_one(".news_Date")
            a = li.select_one("a[href]")
            if date_el is None or a is None:
                continue
            if not year.is_recent_western_date(date_el.get_text(strip=True), today=today):
                continue
            page_has_current = True
            su = urljoin(TMTI_ROOT, a["href"])
            s2 = BeautifulSoup(http.get(su).content, "lxml")
            for link in s2.find_all("a", href=True):
                h = link["href"]
                if "file_download" not in h and ".pdf" not in h.lower():
                    continue
                fn = unquote(parse_qs(urlparse(h).query).get("fname", [""])[0])
                name = fn or link.get_text(strip=True)
                if "申請須知" not in name:
                    continue
                file_url = urljoin(TMTI_ROOT, h)
                if file_url not in seen:
                    seen.add(file_url)
                    out.append((name, file_url))
        if not page_has_current:
            break   # 這頁已無當年度公告（按日期新到舊排，之後只會更舊）
    return out


def _tdri_notices(today=None):
    """tdri IDDI補助 頁 → 點「參考文件」展開 → 抓連結文字/title 含「申請須知」的檔。
    今年 115 已截止、下載下架 → 回 0 筆；明年新一期參考文件重現時自動抓到。"""
    try:
        html = render.render_html_click(TDRI_IDDI, ["參考文件"], timeout=60000)
    except Exception:
        return []
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        name = a.get_text(strip=True) or a.get("title", "")
        if "申請須知" not in name:
            continue
        if not re.search(r"\.pdf|download|file|attach|blob", a["href"], re.I):
            continue
        url = urljoin(TDRI_IDDI, a["href"])
        if url not in seen:
            seen.add(url)
            out.append((name, url))
    return out


def _c99_notices():
    """c_id=99 下載頁 → 連結文字含「申請須知」的直接收下（固定頁、內容持續更新到最新年度）。"""
    soup = BeautifulSoup(http.get(C99_URL).content, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        name = a.get_text(strip=True)
        if "申請須知" in name:
            out.append((name, urljoin(C99_URL, a["href"])))
    return out


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
    out.extend(_keid_cloud_notices())            # 產發局 keid cloud 兩計畫
    out.extend(_keid_citd_notices(today=today))  # 產發局 keid citd 兩計畫
    out.extend(_nqa_notices(today=today))        # 國家品質獎/卓越經營 nqa
    out.extend(_assist_notices(today=today))     # assist 計畫申請快訊
    out.extend(_tmti_notices(today=today))       # 金屬中心 tmti 公告匯集
    out.extend(_tdri_notices(today=today))       # 設計研究院 IDDI（今年截止回0，明年自動抓）
    out.extend(_c99_notices())                   # 產業升級創新平台輔導計畫 c_id=99 下載頁
    return out
