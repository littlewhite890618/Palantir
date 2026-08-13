# -*- coding: utf-8 -*-
"""
sites/doit.py — 經濟部產業技術司 adapter【Cloudflare + render + 多計畫 標題搜尋→詳情】。

產技司的補助分散在多個科專計畫（service.moea.gov.tw/EE514，全站 Cloudflare）。
使用者指定的兩個計畫：
  - A+企業創新研發淬鍊計畫： .../aiip/50.html
  - 無人載具科技創新沙盒：   .../uvtep/24.html

原本抓「最新消息」列表第一頁、Python 端篩標題——但公告會被其他新聞洗到後面幾頁，
用這招會漏抓。改用**該系統內建的標題搜尋**（點開查詢面板、標題欄打「申請須知」送出），
一次拿到跨頁的所有相關公告（含歷史次數的徵案），不受排序影響。
流程（對每個計畫）：
  ① 開列表頁（過 Cloudflare）→ 點查詢面板 → 標題打「申請須知」→ 送出 → 拿搜尋結果
  ② 篩「當年度」的結果 → 逐一 render 詳情頁 → 附件在 wSite/Attachment、檔名在 title（同基隆）
     → looks_like_notice 篩須知類，申請須知優先
※ 頁面要過 Cloudflare（selenium）；但附件檔本身不擋，下載用一般 http.download。
"""
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import render, year

DEPARTMENT = "經濟部產業技術司"
ROOT = "https://service.moea.gov.tw/"
WARMUP = "https://service.moea.gov.tw/EE514/tw/aiip"   # 同網域熱身，過 Cloudflare
SEARCH_KEYWORD = "公告"
# 使用者指定的兩個計畫的「最新消息」列表頁（也是標題搜尋表單所在頁）
NEWS_LISTS = [
    "https://service.moea.gov.tw/EE514/tw/aiip/50.html",    # A+企業創新研發淬鍊計畫
    "https://service.moea.gov.tw/EE514/tw/uvtep/24.html",   # 無人載具科技創新沙盒
]


def _search_title(url, keyword, warmup=WARMUP, wait=15):
    """開列表頁 → 展開查詢面板 → 標題欄打 keyword → 送出 → 回傳搜尋結果 HTML。
    這系統的搜尋框預設摺疊，要先點「查詢」按鈕展開才能操作輸入框。"""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys

    opts = Options()
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    d = webdriver.Chrome(options=opts)
    try:
        # 避免被偵測為 Selenium
        d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",
                          {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"})
        d.get(warmup)
        time.sleep(wait)
        d.get(url)
        time.sleep(wait)
        d.find_element(By.CSS_SELECTOR, "button.conditional_searchbtn").click()   # 展開摺疊面板
        time.sleep(1)
        box = d.find_element(By.ID, "q_stitle")
        box.clear()
        box.send_keys(keyword)
        box.send_keys(Keys.ESCAPE)   # 關掉瀏覽器自動完成建議清單，避免擋住下面的送出鈕
        time.sleep(0.5)
        submit_btn = d.find_element(By.CSS_SELECTOR, "button.btnSubmit")
        d.execute_script("arguments[0].click();", submit_btn)   # 用JS點擊，繞過「元素被遮擋」的檢查
        time.sleep(5)
        return d.page_source
    finally:
        d.quit() #關掉這個 Selenium 開出來的瀏覽器程序


def _search_result_links(html, base_url, today=None):
    """搜尋結果頁 → 篩「當年度」的公告詳情連結（標題已由伺服器端篩過關鍵字，這裡只再篩年度）。"""
    soup = BeautifulSoup(html, "lxml")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        t = a.get_text(strip=True)
        if SEARCH_KEYWORD not in t:
            continue
        if not (year.is_recent_western_date(t, today) or year.has_current_year(t, today)):
            continue
        url = urljoin(base_url, a["href"])
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def _notice_files(html):
    """詳情頁附件 → 檔名在 title（連結文字只是 ODT/PDF 格式標籤）→ 申請須知優先。"""
    soup = BeautifulSoup(html, "lxml")
    candidates = []
    for a in soup.find_all("a", href=True):
        if "Attachment" not in a["href"]:
            continue
        name = a.get("title", "").strip() or a.get_text(strip=True)
        if year.looks_like_notice(name):
            candidates.append((name, urljoin(ROOT, a["href"])))
    priority = [c for c in candidates if "申請須知" in c[0]]
    return priority if priority else candidates


def find_notices(today=None):
    out = []
    for list_url in NEWS_LISTS:
        search_html = _search_title(list_url, SEARCH_KEYWORD)
        for durl in _search_result_links(search_html, list_url, today=today):
            detail_html = render.selenium_fetch(durl, warmup=WARMUP, wait=12, headless=False)
            out.extend(_notice_files(detail_html))
    return out
