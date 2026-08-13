# -*- coding: utf-8 -*-
"""
sites/chiayi_city.py — 嘉義市 adapter【Selenium 全程單一 session：搜尋→點結果→抓附件】。

這站的新聞列表（工商科 News.aspx?n=23&sms=9003）搜尋框預設摺疊：
  ① 點開「單元查詢」摺疊面板 → 主題欄（#jNewsModule_field_2）打「SBIR」→ 送出
  ② 搜尋結果的公告連結 href 是壞的（如「X001.htm?」，網站本身模板問題），
     用瀏覽器「點擊」才能正確導到內容頁（可能是 session 綁定，不能離線用 requests 重抓）
     → 所以全程用同一個 Selenium session 做完，不中途切換回 requests
  ③ 詳情頁附件 → Download.ashx，檔名在 title，格式「[另開新視窗]檔名」要去掉前綴
     → 篩「當年度 + 像須知」（不篩搜尋結果本身的標題年度，因為公告標題不一定帶年份，
        篩選交給附件檔名層——附件檔名一定有年度，同基隆的設計哲學）
※ 下載檔案本身走一般 http.download 沒問題（Download.ashx 是穩定網址，不綁 session）。
"""
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from ..common import year

DEPARTMENT = "嘉義市"
ROOT = "https://economic.chiayi.gov.tw/"
LIST_URL = "https://economic.chiayi.gov.tw/News.aspx?n=23&sms=9003"
SEARCH_KEYWORD = "SBIR"
_TITLE_PREFIX = "[另開新視窗]"


def _notice_files_from_html(html):
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        if "Download.ashx" not in a["href"]:
            continue
        name = a.get("title", "").strip()
        if name.startswith(_TITLE_PREFIX):
            name = name[len(_TITLE_PREFIX):]
        if year.looks_like_notice(name):
            out.append((name, urljoin(ROOT, a["href"])))
    return out


def find_notices(today=None):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By

    opts = Options()
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    d = webdriver.Chrome(options=opts)
    out = []
    try:
        d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",
                          {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"})
        d.get(LIST_URL)
        time.sleep(8)
        d.find_element(By.LINK_TEXT, "單元查詢").click()
        time.sleep(1)
        box = d.find_element(By.ID, "jNewsModule_field_2")
        box.clear()
        box.send_keys(SEARCH_KEYWORD)
        d.find_element(By.ID, "jNewsModule_BtnSend").click()
        time.sleep(5)

        # 搜尋結果連結的 href 是壞的（該站模板問題），只能靠點擊才能正確導頁。
        # 目前觀察只會有 1 筆結果（一則常態性「歡迎提案」公告），故只點第一筆。
        result_links = d.find_elements(By.CSS_SELECTOR, "td[data-title='主題'] a")
        if result_links:
            result_links[0].click()
            time.sleep(3)
            out.extend(_notice_files_from_html(d.page_source))
    finally:
        d.quit()
    return out
