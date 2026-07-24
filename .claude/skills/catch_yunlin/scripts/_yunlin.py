# -*- coding: utf-8 -*-
"""
繞過雲林縣政府網站 Cloudflare 防護、用真瀏覽器下載申請須知 PDF。
自包含腳本：不依賴 extract_schedule_amount.py（inline 了同款 safe_name/CACHE 邏輯），
可獨立搬動/執行。輸出檔會存進共用的 md/data/pdf_cache/，命名規則與主引擎一致，
extract_schedule_amount 重跑時會直接吃到快取、不重抓。
"""
import os, re, time, glob, shutil, hashlib
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ---- 與 extract_schedule_amount.py 同款快取命名，故意 inline 避免跨 skill import ----
def safe_name(dep, name, url):
    base = re.sub(r'[\\/:*?"<>|]+', "_", (dep + "_" + (name or ""))[:60])
    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    return f"{base}_{h}"

HERE = os.path.dirname(os.path.abspath(__file__))                           # .../catch_yunlin/scripts
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))  # n8ntest/
CACHE = os.path.join(PROJECT_ROOT, 'md', 'data', 'pdf_cache')               # 與主引擎共用快取
os.makedirs(CACHE, exist_ok=True)

# ---- 目前寫死單一目標(雲林地方型SBIR申請須知)；要抓別份雲林PDF需改下面三行 ----
URL = ('https://ws.yunlin.gov.tw/Download.ashx?u=LzAwMS9VcGxvYWQvNDAwL3JlbGZpbGUvOTY2Mi81ODM5NzIv'
       'ZjM4YTgwZmMtN2JhMC00NDZjLWEzYjQtYmUwMWJhNTE5NTIzLnBkZg%3d%3d'
       '&n=MTE15bm05bqm6Zuy5p6X57ij5pS%2f5bqc5Zyw5pa55Z6LU0JJUuWFrOWRiuizh%2baWmS3lhazmloflhazlkYrniYh2MS5wZGY%3d')
DEP, NAME = '雲林縣政府', '地方型SBIR申請須知.pdf'
DL = os.path.join(HERE, '_dl')
os.makedirs(DL, exist_ok=True)
for f in glob.glob(DL + '/*'):
    os.remove(f)

opts = Options()
opts.add_argument('--disable-gpu')
opts.add_argument('--no-sandbox')
opts.add_argument('--window-size=1280,900')
opts.add_argument('--disable-blink-features=AutomationControlled')
opts.add_experimental_option('excludeSwitches', ['enable-automation'])
opts.add_experimental_option('useAutomationExtension', False)
opts.add_experimental_option('prefs', {
    'download.default_directory': DL,
    'download.prompt_for_download': False,
    'plugins.always_open_pdf_externally': True,
})
d = webdriver.Chrome(options=opts)
try:
    d.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument',
                      {'source': "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"})
    d.execute_cdp_cmd('Page.setDownloadBehavior', {'behavior': 'allow', 'downloadPath': DL})
    d.get('https://www.yunlin.gov.tw/')
    time.sleep(8)
    d.get(URL)
    time.sleep(8)
    got = None
    for _ in range(40):
        time.sleep(1)
        fs = [f for f in glob.glob(DL + '/*') if not f.endswith('.crdownload')]
        if fs and os.path.getsize(fs[0]) > 1000:
            got = fs[0]; break
    if got:
        with open(got, 'rb') as fh:
            head = fh.read(4)
        stem = safe_name(DEP, NAME, URL)
        dest = os.path.join(CACHE, stem + '.pdf')
        shutil.copy(got, dest)
        print('DOWNLOADED size=%d head=%r -> %s' % (os.path.getsize(got), head, os.path.basename(dest)))
    else:
        print('NO FILE. title=%r current=%s' % (d.title, d.current_url))
finally:
    d.quit()
