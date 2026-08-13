# -*- coding: utf-8 -*-
"""
common/http.py — 共用連線層（一般 requests）。

政府網站很多用老舊/過時的 TLS 設定，Python 預設的安全等級會連不上（SSLError）。
這裡用 LegacyTLSAdapter 把安全等級降到 SECLEVEL=1、並關掉憑證驗證，才連得上。
（此段邏輯複製自既有 extract_schedule_amount.py，改寫成本專案獨立模組，不 import。）

對外主要用 get(url)：回傳 requests.Response。
"""
import os
import re
import ssl
import glob
import hashlib
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from urllib3.util.retry import Retry

# 我們刻意關掉憑證驗證來連老政府站，這行把隨之而來的警告訊息關掉，畫面才乾淨。
requests.packages.urllib3.disable_warnings()

# 假裝成一般 Chrome 瀏覽器，並偏好台灣繁中內容（有些站會看 UA / 語言決定回什麼）。
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Accept": "*/*",
}


class LegacyTLSAdapter(HTTPAdapter):
    """遷就老政府站的過時 TLS：降安全等級 + 不驗證憑證，否則會 SSLError 連不上。"""

    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")   # 降安全等級才連得上舊站
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE #不嚴格檢查它的憑證
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def make_session():
    """建立一個掛好 headers、LegacyTLSAdapter 與重試機制的 requests Session。"""
    s = requests.Session()
    s.headers.update(HEADERS)
    retry = Retry(
        total=3,                            # 最多重試3次（加最初那次，最多打4次）
        backoff_factor=1,                   # 重試間隔遞增：1s、2s、4s
        status_forcelist=[502, 503, 504],   # 只有這些「伺服器暫時性錯誤」才重試
                                             # （不含404/403，那是權限/網址問題，重試沒用）
        allowed_methods=frozenset(["GET", "POST"]),  # POST目前只用在查詢/搜尋表單，重送無副作用
    )
    s.mount("https://", LegacyTLSAdapter(max_retries=retry))
    return s


# 模組層級共用一個 session（重複用同一條連線，省資源）。
_session = None


def _ensure_session():
    global _session
    if _session is None:
        _session = make_session()
    return _session


def get(url, timeout=30, **kwargs):
    """抓一個網址，回傳 requests.Response。老站的 TLS/憑證問題已在此處理掉。"""
    kwargs.setdefault("verify", False)
    return _ensure_session().get(url, timeout=timeout, **kwargs)


def post(url, timeout=30, **kwargs):
    """POST 一個網址（例如站內搜尋表單），回傳 requests.Response。"""
    kwargs.setdefault("verify", False)
    return _ensure_session().post(url, timeout=timeout, **kwargs)


def _guess_ext(content):
    """用檔案開頭的 magic bytes 猜副檔名（沒有可靠副檔名時用）。"""
    if content[:4] == b"%PDF" or b"%PDF" in content[:1024]:
        return "pdf"
    if content[:2] == b"PK":          # docx / odt / xlsx / zip 都是 zip 家族
        return "zip"
    return "bin"


def _safe_name(label, url):
    """組安全檔名：中文前綴去掉特殊字（截 50 字）+ url 的 md5 短碼（避免重名、可比對）。"""
    base = re.sub(r'[\\/:*?"<>|]+', "_", (label or "file"))[:50]
    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    return f"{base}_{h}"


def download(url, dest_dir, label=""):
    """下載 url 到 dest_dir，回傳本地路徑。
    以 url 的 md5 短碼做快取：只要下載過（檔名以該碼結尾），就直接回傳、不重抓。"""
    os.makedirs(dest_dir, exist_ok=True)
    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    cached = glob.glob(os.path.join(dest_dir, f"*_{h}.*"))   # 找有沒有下載過
    if cached:
        return cached[0]
    content = get(url).content                               # .content = 原始 bytes
    ext = _guess_ext(content)
    path = os.path.join(dest_dir, f"{_safe_name(label, url)}.{ext}")
    with open(path, "wb") as f:                              # "wb" = 二進位寫入
        f.write(content)
    return path
