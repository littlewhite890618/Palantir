# -*- coding: utf-8 -*-
"""
common/textio.py — 文字層：下載申請須知檔（PDF/DOCX/ODT/ZIP）並抽出純文字。

由 .claude/skills/extract_schedule_amount/scripts/extract_schedule_amount.py 搬入，
行為刻意保持不變（含 legacy SSL 修正、快取、zip 內中文檔名修正、NFKC 正規化）。
供 subsidy_crawler 套件與既有 skill 共用，避免跨 .claude/skills 的脆弱匯入路徑。

對外主要 API：
    session()                建立帶 legacy TLS 的 requests session
    download(sess, url, dep, name) -> (path, ext, status)
    extract_text(path, ext)  -> (text, title)   ext: pdf/docx/odt/zip
    normalize(text)          -> NFKC + 全形轉半形後的字串
"""
import os
import re
import io
import ssl
import time
import glob
import shutil
import tempfile
import hashlib
import zipfile
import unicodedata

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

requests.packages.urllib3.disable_warnings()

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "..", "data", "pdf_cache")
os.makedirs(CACHE, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Accept": "*/*",
}


class LegacyTLSAdapter(HTTPAdapter):
    """部分政府站台用舊 TLS/低 SECLEVEL；放寬密碼套件與憑證檢查以順利連線。"""
    def init_poolmanager(self, *a, **k):
        ctx = create_urllib3_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        k["ssl_context"] = ctx
        return super().init_poolmanager(*a, **k)


def session():
    s = requests.Session()
    s.headers.update(HEADERS)
    s.mount("https://", LegacyTLSAdapter())
    return s


# ---------- 下載 ----------
def safe_name(dep, name, url):
    base = re.sub(r'[\\/:*?"<>|]+', "_", (dep + "_" + (name or ""))[:60])
    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    return f"{base}_{h}"


def detect_ext(content, ctype, url):
    if content[:4] == b"%PDF" or b"%PDF" in content[:2048]:
        return "pdf"
    if content[:2] == b"PK":  # zip-based: docx/odt/xlsx/zip
        try:
            z = zipfile.ZipFile(io.BytesIO(content))
            names = z.namelist()
            if "word/document.xml" in names:
                return "docx"
            if "content.xml" in names and any("opendocument" in n or n == "mimetype" for n in names):
                mt = z.read("mimetype").decode("ascii", "ignore") if "mimetype" in names else ""
                if "text" in mt:
                    return "odt"
                return "odt" if "content.xml" in names else "zip"
            return "zip"
        except Exception:
            return "zip"
    low = url.lower()
    for e in ("pdf", "docx", "odt", "zip"):
        if low.split("?")[0].endswith("." + e):
            return e
    if ctype and "pdf" in ctype:
        return "pdf"
    return "unknown"


def download(sess, url, dep, name):
    """回傳 (path, ext, status)。已快取則回 status='快取'；非檔案/失敗則 path=None。"""
    url = url.strip()
    # 去除 chrome-extension:// 前綴，取最後一個真實 https 網址
    if 'chrome-extension' in url and 'https://' in url:
        url = 'https://' + url.split('https://')[-1]
    else:
        m = re.search(r'https?://.*', url)
        if m:
            url = m.group(0)
    stem = safe_name(dep, name, url)
    for f in os.listdir(CACHE):
        if f.startswith(stem + "."):
            p = os.path.join(CACHE, f)
            return p, f.rsplit(".", 1)[1], "快取"
    try:
        r = sess.get(url, timeout=60, verify=False, allow_redirects=True)
        if r.status_code != 200:
            # 403 多為 Cloudflare 擋 requests → 改用真瀏覽器繞過（如雲林縣）
            if r.status_code == 403:
                return download_via_browser(url, dep, name)
            return None, None, f"HTTP{r.status_code}"
        content = r.content
        ext = detect_ext(content, r.headers.get("Content-Type", ""), url)
        if ext == "unknown":
            return None, None, "非檔案(可能是網頁)"
        p = os.path.join(CACHE, stem + "." + ext)
        with open(p, "wb") as fh:
            fh.write(content)
        return p, ext, "成功"
    except Exception as e:
        return None, None, "下載錯誤:" + type(e).__name__


def download_via_browser(url, dep, name):
    """Cloudflare 擋 requests(403) 時的後備：用真瀏覽器(Selenium)繞過並下載。
    由 catch_yunlin skill 的作法一般化而來（不寫死雲林 URL）：
    非 headless + 反自動化偵測；先訪問站台首頁取得 CF 通行，再抓下載 URL。
    需要環境有 Chrome + selenium；缺任一則回 (None, None, 錯誤)。回傳同 download()。"""
    stem = safe_name(dep, name, url)
    for f in os.listdir(CACHE):                     # 已快取則直接用
        if f.startswith(stem + "."):
            p = os.path.join(CACHE, f)
            return p, f.rsplit(".", 1)[1], "快取"
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except Exception:
        return None, None, "瀏覽器不可用(無selenium)"
    from urllib.parse import urlsplit

    dldir = tempfile.mkdtemp(prefix="brdl_")
    opts = Options()
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--disable-blink-features=AutomationControlled")   # 反自動化偵測
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_experimental_option("prefs", {
        "download.default_directory": dldir,
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,      # PDF 直接下載不預覽
    })
    try:
        drv = webdriver.Chrome(options=opts)
    except Exception as e:
        shutil.rmtree(dldir, ignore_errors=True)
        return None, None, "瀏覽器不可用:" + type(e).__name__
    try:
        drv.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",
                            {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"})
        drv.execute_cdp_cmd("Page.setDownloadBehavior", {"behavior": "allow", "downloadPath": dldir})
        sp = urlsplit(url)
        drv.get(f"{sp.scheme}://{sp.netloc}/")      # 先取 CF 通行證（cookie）
        time.sleep(8)
        drv.get(url)                                # 再抓下載連結
        time.sleep(5)
        got = None
        for _ in range(40):                         # 最多等 ~40s 下載完成
            time.sleep(1)
            fs = [f for f in glob.glob(dldir + "/*") if not f.endswith(".crdownload")]
            if fs and os.path.getsize(fs[0]) > 1000:
                got = fs[0]
                break
        if not got:
            return None, None, "瀏覽器下載無檔案"
        with open(got, "rb") as fh:
            content = fh.read()
        ext = detect_ext(content, "", url)
        if ext == "unknown":
            return None, None, "瀏覽器取得非檔案"
        dest = os.path.join(CACHE, stem + "." + ext)
        shutil.copy(got, dest)
        return dest, ext, "成功(瀏覽器)"
    except Exception as e:
        return None, None, "瀏覽器錯誤:" + type(e).__name__
    finally:
        try:
            drv.quit()
        except Exception:
            pass
        shutil.rmtree(dldir, ignore_errors=True)


# ---------- 抽文字 ----------
def extract_pdf(path):
    import pdfplumber
    parts, title = [], ""
    with pdfplumber.open(path) as pdf:
        try:
            title = (pdf.metadata or {}).get("Title", "") or ""
        except Exception:
            title = ""
        for pg in pdf.pages:
            t = pg.extract_text() or ""
            parts.append(t)
            for tb in (pg.extract_tables() or []):
                for row in tb:
                    parts.append(" ".join(c or "" for c in row))
    return "\n".join(parts), title.strip()


def extract_docx(path):
    from docx import Document
    from docx.oxml.ns import qn
    d = Document(path)
    parts = [p.text for p in d.paragraphs]
    for tb in d.tables:
        for row in tb.rows:
            # 直接讀該列的 <w:tc> 文字，避開 python-docx 在「合併儲存格」上
            # 用 row.cells 會拋 ValueError: no `tc` element at grid_offset 的問題。
            cells = []
            for tc in row._tr.findall(qn("w:tc")):
                cells.append("".join((t.text or "") for t in tc.findall(".//" + qn("w:t"))))
            parts.append(" ".join(cells))
    core = d.core_properties
    return "\n".join(parts), (core.title or "").strip()


def extract_odt(path):
    from odf.opendocument import load
    from odf import text as odftext, teletype
    doc = load(path)
    parts = []
    for el in doc.getElementsByType(odftext.P):
        parts.append(teletype.extractText(el))
    for el in doc.getElementsByType(odftext.H):
        parts.append(teletype.extractText(el))
    return "\n".join(parts), ""


def _zip_realname(nm):
    # zip 內中文檔名編碼修正（cp437 -> big5/utf-8）
    for enc in ("big5", "utf-8"):
        try:
            return nm.encode("cp437").decode(enc)
        except Exception:
            pass
    return nm


def extract_zip(path):
    z = zipfile.ZipFile(path)
    cands = [i for i in z.infolist()
             if i.filename.lower().endswith((".pdf", ".docx", ".odt"))]
    # 優先檔名含「申請須知」
    cands.sort(key=lambda i: 0 if "須知" in _zip_realname(i.filename) else 1)
    for info in cands:
        low = info.filename.lower()
        ext = "pdf" if low.endswith(".pdf") else ("docx" if low.endswith(".docx") else "odt")
        tmp = path + ".inner." + ext
        with open(tmp, "wb") as fh:
            fh.write(z.read(info))
        try:
            txt, title = extract_text(tmp, ext)
        except Exception:
            txt, title = "", ""
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass
        if "申請須知" in txt or "須知" in _zip_realname(info.filename):
            return txt, (title or _zip_realname(info.filename))
    return "", ""


def extract_text(path, ext):
    if ext == "pdf":
        return extract_pdf(path)
    if ext == "docx":
        return extract_docx(path)
    if ext == "odt":
        return extract_odt(path)
    if ext == "zip":
        return extract_zip(path)
    return "", ""


# ---------- 正規化 ----------
def normalize(s):
    # NFKC：相容表意字（U+F900-FAFF）→標準字、全形→半形、％→%
    s = unicodedata.normalize("NFKC", s)
    out = []
    for ch in s:
        o = ord(ch)
        if 0xFF10 <= o <= 0xFF19:      # 全形 0-9
            out.append(chr(o - 0xFEE0))
        elif o == 0x3000:              # 全形空白
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)
