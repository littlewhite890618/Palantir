"""
export_subsidies.py — 把 subsidies 資料表匯出成「加密過的 JSON」，給 GitHub Pages 靜態站用。

流程：PostgreSQL --> list[dict] --> JSON --> AES-GCM 加密 --> React/public/subsidies.enc.json

設計重點（改參數前務必先讀）：
1. 日期一律轉 ISO 字串（YYYY-MM-DD）。JSON 沒有日期型別，不轉會直接 TypeError；
   而且前端 HomePage.js 的 getDeadlineBucket() 是用 new Date(deadline) 解析，
   只有 ISO 格式才保證所有瀏覽器解析一致。換格式會讓「期限」篩選壞掉。
2. 加密參數（PBKDF2 迭代數/salt 長度/IV 長度）必須與前端 subsidyService.js 完全一致，
   對不上的症狀是「解密失敗」，且跟「密碼打錯」長得一模一樣、無從分辨。
   要改參數就兩邊一起改。
3. 密碼只從環境變數 SUBSIDY_PASSWORD 讀，或互動式輸入。絕不寫進檔案、絕不進 commit。
4. 本環境 console 是 cp950，印中文會報錯（見 extract_schedule_amount/SKILL.md 已知坑 #3），
   所以這支程式的訊息一律用英文。
"""

import os
import sys
import gzip
import json
import base64
import getpass
import datetime
import decimal

import psycopg2
from psycopg2.extras import RealDictCursor
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ── 加密參數：改這裡就要同步改前端 subsidyService.js ──────────────
PBKDF2_ITERATIONS = 200_000   # 拖慢暴力破解；瀏覽器端約需 0.3-1 秒
SALT_BYTES = 16
IV_BYTES = 12                 # AES-GCM 標準 nonce 長度，Web Crypto 預期 12
KEY_BITS = 256
ENVELOPE_VERSION = 1
# ─────────────────────────────────────────────────────────

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
DEFAULT_OUT = os.path.join(PROJECT_ROOT, "React", "public", "subsidies.enc.json")
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")


def load_env(path):
    """讀 .env 成 dict。不引入 python-dotenv，只為了少一個依賴。"""
    conf = {}
    if not os.path.exists(path):
        return conf
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            conf[k.strip()] = v.strip()
    return conf


def json_default(o):
    """
    JSON 不認得的型別在這裡轉。
    date/datetime -> ISO 字串（前端 new Date() 靠這個）
    Decimal -> float（金額欄位理論上是文字，但防資料表型別變動）
    """
    if isinstance(o, (datetime.datetime, datetime.date)):
        return o.isoformat()
    if isinstance(o, datetime.time):
        return o.isoformat()
    if isinstance(o, decimal.Decimal):
        return float(o)
    if isinstance(o, (bytes, bytearray)):
        return base64.b64encode(o).decode("ascii")
    raise TypeError("Not JSON serializable: %r" % type(o))


def fetch_rows(conf):
    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5434")),
        dbname=conf.get("POSTGRES_DB", "palentir_test_db"),
        user=conf.get("POSTGRES_USER", "admin"),
        password=conf.get("POSTGRES_PASSWORD", ""),
    )
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM subsidies ORDER BY id")
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def encrypt(plaintext_bytes, password):
    """AES-GCM 加密。回傳可直接 json.dump 的信封 dict。"""
    salt = os.urandom(SALT_BYTES)
    iv = os.urandom(IV_BYTES)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_BITS // 8,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    key = kdf.derive(password.encode("utf-8"))

    # cryptography 的 AESGCM.encrypt 回傳 ciphertext || tag(16 bytes)，
    # 這正好是 Web Crypto 的 decrypt 預期的格式，不需另外拆出 tag。
    ct = AESGCM(key).encrypt(iv, plaintext_bytes, None)

    b64 = lambda b: base64.b64encode(b).decode("ascii")
    return {
        "v": ENVELOPE_VERSION,
        "kdf": "PBKDF2-SHA256",
        "iterations": PBKDF2_ITERATIONS,
        # 前端據此決定要不要解壓。寫成欄位而不是寫死，
        # 是為了日後想換/停用壓縮時不會與舊檔不相容。
        "compression": "gzip",
        "salt": b64(salt),
        "iv": b64(iv),
        "data": b64(ct),
        # 這兩個是明文（讓密碼畫面能顯示資料新舊，不解密也讀得到）。
        # 不放筆數等內容資訊。
        "exported_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT

    password = os.environ.get("SUBSIDY_PASSWORD")
    if not password:
        password = getpass.getpass("Password to encrypt with: ")
    if not password:
        print("ERROR: empty password, aborted.")
        return 1

    conf = load_env(ENV_PATH)
    rows = fetch_rows(conf)
    if not rows:
        print("ERROR: query returned 0 rows, aborted (refusing to publish empty data).")
        return 1

    # ensure_ascii=False：中文原樣存 UTF-8，不要變成 \uXXXX（檔案小很多）
    raw = json.dumps(rows, default=json_default, ensure_ascii=False).encode("utf-8")

    # 先壓縮再加密（順序很重要：加密後的資料是高亂度的，再壓就壓不動了）。
    # 實測 201 筆：1015 KB -> 213 KB，最終檔案 1354 KB -> 284 KB。
    # 前端用瀏覽器內建的 DecompressionStream('gzip') 還原，不需任何套件。
    plaintext = gzip.compress(raw, 9)
    envelope = encrypt(plaintext, password)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(envelope, f)

    print("rows exported     : %d" % len(rows))
    print("json size         : %d bytes" % len(raw))
    print("gzipped size      : %d bytes (%.1f%%)" % (len(plaintext), 100.0 * len(plaintext) / len(raw)))
    print("encrypted file    : %s" % out_path)
    print("encrypted size    : %d bytes" % os.path.getsize(out_path))
    print("columns           : %s" % ", ".join(rows[0].keys()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
