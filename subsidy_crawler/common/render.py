# -*- coding: utf-8 -*-
"""
common/render.py — 難站用的「開瀏覽器」抓取。

有些站（SPA）內容要等 JavaScript 跑完才長出來，純 requests 抓到的是空殼。
這裡用 Playwright 真的開一個 chromium、等頁面載完，再把「渲染後的 HTML」拿回來。
（雲林那種 Cloudflare 反偵測，之後再加 selenium 版。）
"""
from playwright.sync_api import sync_playwright


def render_html(url, wait_selector=None, timeout=45000):
    """開瀏覽器載入 url，等 JS 跑完，回傳渲染後的完整 HTML。
    wait_selector: 若指定，會等這個 CSS 選擇器出現才擷取（確保資料真的載進來了）。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)     # headless=不開視窗，背景跑
        page = browser.new_page()
        # wait_until="networkidle"：等網路安靜下來（SPA 的資料通常靠背景請求載入）
        page.goto(url, timeout=timeout, wait_until="networkidle")
        if wait_selector:
            page.wait_for_selector(wait_selector, timeout=timeout)
        html = page.content()                          # 這時拿到的是「渲染後」的 HTML
        browser.close()
    return html


def render_html_click(url, click_texts, timeout=45000, settle_ms=3000):
    """開瀏覽器載入 url，依序嘗試點擊「文字符合 click_texts 之一」的元素（點到即停），
    等 settle_ms 後回傳渲染後 HTML。用於「內容要點某個分頁/按鈕才展開」的站（如 tdri 參考文件）。
    找不到可點元素時不報錯，回傳未點擊的頁面 HTML（呼叫端自行判斷有無目標檔）。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=timeout, wait_until="networkidle")
        for txt in click_texts:
            try:
                page.get_by_text(txt, exact=False).first.click(timeout=5000)
                page.wait_for_timeout(settle_ms)
                break
            except Exception:
                continue   # 這個文字點不到，換下一個候選
        html = page.content()
        browser.close()
    return html


def selenium_fetch(url, warmup="https://www.yunlin.gov.tw/", wait=8, headless=False):
    """用「反偵測 Selenium」開真 Chrome 抓頁面，繞過 Cloudflare 這類機器人偵測。
    先逛 warmup 首頁拿通行 cookie，再開目標頁，回傳渲染後 HTML。
    （反偵測招數複製自既有 catch_yunlin/_yunlin.py，改成通用回傳 HTML。）"""
    import time
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--disable-blink-features=AutomationControlled")   # 關掉自動化旗標
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    d = webdriver.Chrome(options=opts)
    try:
        # 把 navigator.webdriver 從 true 改成 undefined（藏起「我是機器人」的特徵）
        d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",
                          {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"})
        if warmup:
            d.get(warmup)     # 先逛首頁熱身，讓 Cloudflare 挑戰過關、拿到通行 cookie
            time.sleep(wait)
        d.get(url)            # 再開真正要抓的頁
        time.sleep(wait)
        return d.page_source
    finally:
        d.quit()


def selenium_search(url, input_selector, keyword, submit_selector=None,
                    warmup="https://www.yunlin.gov.tw/", wait=8):
    """反偵測 Selenium：開頁 → 在搜尋框(input_selector)打 keyword → 送出 → 回傳結果頁 HTML。
    submit_selector 有給就點它送出，否則對輸入框按 Enter。"""
    import time
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
        d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",
                          {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"})
        if warmup:
            d.get(warmup)
            time.sleep(wait)
        d.get(url)
        time.sleep(wait)
        box = d.find_element(By.CSS_SELECTOR, input_selector)   # 找到搜尋框
        box.clear()
        box.send_keys(keyword)                                  # 打字
        if submit_selector:
            d.find_element(By.CSS_SELECTOR, submit_selector).click()   # 點送出鈕
        else:
            box.send_keys(Keys.RETURN)                          # 或按 Enter
        time.sleep(wait)                                        # 等結果載入
        return d.page_source
    finally:
        d.quit()


def selenium_download(url, dest_dir, label="", warmup="https://www.yunlin.gov.tw/", wait=8):
    """用反偵測 Selenium『瀏覽器下載』一個檔（連檔案也擋 Cloudflare 的站用）。回傳本地路徑。
    以 url 的 md5 做快取（下載過就直接回傳）。（下載邏輯複製自既有 catch_yunlin/_yunlin.py。）"""
    import os, time, glob, shutil, hashlib
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from . import http   # 重用 _safe_name / _guess_ext（命名與快取一致）

    os.makedirs(dest_dir, exist_ok=True)
    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    cached = glob.glob(os.path.join(dest_dir, f"*_{h}.*"))
    if cached:                                  # 快取命中就不重抓
        return cached[0]

    tmp = os.path.join(dest_dir, "_dl_tmp")     # 瀏覽器先下載到暫存資料夾
    os.makedirs(tmp, exist_ok=True)
    for f in glob.glob(tmp + "/*"):
        try:
            os.remove(f)
        except OSError:
            pass

    opts = Options()
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_experimental_option("prefs", {
        "download.default_directory": tmp,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,   # PDF 用下載的、不要用看的
    })
    d = webdriver.Chrome(options=opts)
    try:
        d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",
                          {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"})
        d.execute_cdp_cmd("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": tmp})
        if warmup:
            d.get(warmup)
            time.sleep(wait)
        d.get(url)
        time.sleep(wait)
        got = None
        for _ in range(40):                     # 最多等 40 秒讓檔案下載完成
            time.sleep(1)
            fs = [f for f in glob.glob(tmp + "/*") if not f.endswith(".crdownload")]
            if fs and os.path.getsize(fs[0]) > 1000:
                got = fs[0]
                break
        if not got:
            return None
        with open(got, "rb") as fh:
            ext = http._guess_ext(fh.read(2048))
        dest = os.path.join(dest_dir, http._safe_name(label, url) + "." + ext)
        shutil.move(got, dest)
        return dest
    finally:
        d.quit()
