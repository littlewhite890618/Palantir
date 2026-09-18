# -*- coding: utf-8 -*-
"""
subsidy_crawler/common/db.py — 把管線最終去重結果同步進 PostgreSQL 的 subsidies 表。

現階段策略（刻意簡化，OpenSpec change pipeline-db-sync 定案）：
    每次呼叫都是「整表 TRUNCATE + 全量 INSERT」，不做既有列比對/UPDATE，
    也不處理「這次沒抓到但資料庫裡有」的列——資料庫每次同步完就是這次
    管線輸出的完整快照。比對式增量同步（判斷是否為同一筆補助案、內容
    變更時更新而非整表重建）留待下一輪 change。

安全機制：
    - 只寫「成功列」（萃取模型欄位有值），失敗列不進資料庫。
    - 空結果（0筆成功）直接中止，不清空既有資料，避免管線異常時誤刪。
    - 清空前先自動 pg_dump 備份到本機（data/db_backup_*.sql，不進版控）。
    - 整段用交易包住：TRUNCATE + 逐筆 INSERT + 驗證筆數，全部通過才 COMMIT，
      任何步驟失敗就 ROLLBACK，資料庫回到執行前狀態。

用法：
    from .common import db
    db.sync_to_db(csv_path)
"""
import os
import csv
import time
import subprocess
import datetime

import psycopg2

HERE = os.path.dirname(os.path.abspath(__file__))
# HERE = subsidy_crawler/common/，上兩層才是 repo 根目錄（.env 所在處）。
ENV_PATH = os.path.abspath(os.path.join(HERE, "..", "..", ".env"))
DATA_DIR = os.path.abspath(os.path.join(HERE, "..", "data"))

# subsidies 表欄位 ← subsidy_crawler 15 欄 CSV 欄位（見 openspec pipeline-db-sync spec）。
# amount 另外處理（金額上限為空時退用補助比例）；start_date/subsidy_timeline 無對應來源、固定留空；
# 部門(原始)/萃取模型/規則交叉檢查/備註 是內部品管欄位，不寫入。
_FIELD_MAP = {
    "title": "標題",
    "category": "申請機關",
    "deadline": "申請截止日期",
    "description": "描述",
    "source_url": "連結",
    "eligibility": "申請資格",
    "required_documents": "應備資料",
    "application_method": "申請方式",
    "contact_window": "諮詢窗口",
}
_DB_COLUMNS = ("title", "category", "amount", "deadline", "description",
               "source_url", "eligibility", "required_documents",
               "application_method", "contact_window", "start_date", "subsidy_timeline")


def _load_env():
    """讀 repo 根目錄 .env 成 dict（手寫 parser，不用 python-dotenv，
    沿用 export_subsidies.py 的既有做法）。"""
    conf = {}
    if not os.path.exists(ENV_PATH):
        return conf
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            conf[k.strip()] = v.strip()
    return conf


def connect():
    """建立資料庫連線（公開函式，dev_api.py 等其他模組共用同一套連線設定，不重寫）。"""
    conf = _load_env()
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5434")),
        dbname=conf.get("POSTGRES_DB", "palentir_test_db"),
        user=conf.get("POSTGRES_USER", "admin"),
        password=conf.get("POSTGRES_PASSWORD", ""),
    )


def _load_success_rows(csv_path):
    """讀最終結果 CSV，只留「萃取模型」非空的成功列
    （跟 extract_fields.py::load_done() 判斷「是否成功」用同一個欄位/邏輯）。"""
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if (r.get("萃取模型") or "").strip()]


def _map_row(r):
    """subsidy_crawler 15 欄 → subsidies 12 欄。金額上限為空時退用補助比例
    （跟萃取引擎本身「金額上限優先於比例」的既有邏輯一致）。"""
    out = {db_col: (r.get(src_col) or "").strip() for db_col, src_col in _FIELD_MAP.items()}
    out["amount"] = (r.get("補助金額上限") or "").strip() or (r.get("補助比例") or "").strip()
    out["start_date"] = None
    out["subsidy_timeline"] = None
    return out


def _backup():
    """清空前先 pg_dump 備份到本機（沿用 md/DEPLOY_FRONTEND.md 既有的手動慣例指令）。
    備份失敗就丟例外中止——備份是清空前的必要前提，備份失敗等於沒有安全網，
    不能因為備份失敗就跳過備份直接往下清空。回傳備份檔案路徑。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(DATA_DIR, f"db_backup_{ts}.sql")
    conf = _load_env()
    dbname = conf.get("POSTGRES_DB", "palentir_test_db")
    try:
        result = subprocess.run(
            ["docker", "exec", "postgres", "pg_dump", "-U", "admin", dbname],
            capture_output=True, timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"pg_dump 備份失敗（無法執行 docker，container 可能未啟動）：{e}") from e
    if result.returncode != 0:
        raise RuntimeError(
            f"pg_dump 備份失敗（exit={result.returncode}）：{result.stderr.decode('utf-8', 'replace')}"
        )
    with open(path, "wb") as f:
        f.write(result.stdout)
    return path


def sync_to_db(csv_path):
    """把 csv_path 的最終去重結果（成功列）整批同步進 subsidies 表。
    整表 TRUNCATE + INSERT，交易包住，寫入前備份，驗證筆數才 COMMIT，
    任一步驟失敗即 rollback、資料庫回到執行前狀態。回傳實際寫入筆數。"""
    t0 = time.time()
    rows = _load_success_rows(csv_path)
    if not rows:
        raise RuntimeError("成功列數為 0，拒絕同步（避免用空結果清空既有資料庫）。")

    backup_path = _backup()
    print(f"  已備份：{backup_path}")

    mapped = [_map_row(r) for r in rows]

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE subsidies")
            insert_sql = (
                "INSERT INTO subsidies (" + ", ".join(_DB_COLUMNS) + ") "
                "VALUES (" + ", ".join(["%s"] * len(_DB_COLUMNS)) + ")"
            )
            for m in mapped:
                cur.execute(insert_sql, [m[c] for c in _DB_COLUMNS])
            cur.execute("SELECT count(*) FROM subsidies")
            (actual,) = cur.fetchone()
            if actual != len(mapped):
                # 不在這裡 rollback：讓例外往下拋，由外層 except 統一處理，避免重複呼叫 rollback()。
                raise RuntimeError(
                    f"寫入後筆數對不上（預期 {len(mapped)}、資料庫實際 {actual}），已 rollback、資料庫維持執行前狀態。"
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    elapsed = time.time() - t0
    print(f"  已寫入 {len(mapped)} 筆到 subsidies 表（耗時 {elapsed:.1f}s，備份：{backup_path}）。")
    return len(mapped)
