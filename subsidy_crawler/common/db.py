# -*- coding: utf-8 -*-
"""
subsidy_crawler/common/db.py — 把管線最終去重結果「增量」同步進 PostgreSQL 待審表。

現階段策略（OpenSpec change pipeline-incremental-review-queue 定案）：
    - 管線不再寫正式表 subsidies（原本的整表 TRUNCATE + 全量 INSERT 已移除）。
      subsidies 只能透過 approve_pending() 審核通過寫入；現有內容就是比對起點。
    - 身分 key＝(category＝申請機關, source_url＝連結)。本次成功列的 key 已存在於
      subsidies 或 subsidies_pending（不論 pending/approved/rejected）→ 已知案，跳過，
      不更新任何內容（同一份 PDF 重萃取，描述/資格等文字本來就會變，更新只會製造雜訊）。
    - key 不存在 → 新案，寫進 subsidies_pending（status=pending）。另外跟 subsidies 裡
      「同機關、同網域」的案子比標題相似度，≥ postprocess.TITLE_SIM_TH 就在 suspected_dup_of
      記下舊案 id（網址換了的舊案），但仍然進待審，不自動跳過——交給人工判斷。
      要求同網域：各縣市地方型 SBIR 的申請機關都是中小企業署、標題只差縣市名，
      只看機關＋標題會把金門標成苗栗的舊案；各縣市 SBIR 網站網域不同，加這個條件就分得開。
    - 這次沒抓到、但資料庫裡有的案子：不處理。

安全機制：
    - 只處理「成功列」（萃取模型欄位有值），失敗列不進資料庫。
    - 空結果（0筆成功）直接中止，通常代表管線異常，交給上層寫告警。
    - 有新案要寫入時才先 pg_dump 備份到本機（data/db_backup_*.sql，不進版控）；
      沒有新案就完全不寫資料庫，也不備份。
    - 整段用交易包住：INSERT + 驗證新增筆數，全部通過才 COMMIT，
      任何步驟失敗就 ROLLBACK，資料庫回到執行前狀態。

用法：
    from .common import db
    stats = db.sync_new_to_pending(csv_path, run_at)
    db.approve_pending([id, ...]) / db.reject_pending([id, ...])   # 給審核頁用
"""
import os
import csv
import time
import subprocess
import datetime
from urllib.parse import urlsplit

import psycopg2

HERE = os.path.dirname(os.path.abspath(__file__))
# HERE = subsidy_crawler/common/，上兩層才是 repo 根目錄（.env 所在處）。
ENV_PATH = os.path.abspath(os.path.join(HERE, "..", "..", ".env"))
DATA_DIR = os.path.abspath(os.path.join(HERE, "..", "data"))
NEW_THIS_RUN_CSV = os.path.join(DATA_DIR, "new_this_run.csv")

# subsidies 表欄位 ← subsidy_crawler 15 欄 CSV 欄位（見 openspec subsidy-db-sync spec）。
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

# 待審表：內容欄位型別跟 subsidies 一致（subsidies 是手動建的，schema 見 data/db_backup_*.sql），
# 另加審核狀態欄位。repo 沒有 migration 工具，用冪等的 CREATE TABLE IF NOT EXISTS 第一次執行時自建。
_PENDING_DDL = """
CREATE TABLE IF NOT EXISTS subsidies_pending (
    id serial PRIMARY KEY,
    title character varying(255) NOT NULL,
    category character varying(50),
    amount character varying(50),
    start_date character varying(50),
    deadline text,
    description text,
    source_url text,
    subsidy_timeline text,
    eligibility text,
    required_documents text,
    application_method text,
    contact_window text,
    status character varying(10) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected')),
    first_seen_at timestamp without time zone NOT NULL,
    reviewed_at timestamp without time zone,
    suspected_dup_of integer,
    UNIQUE (category, source_url)
)
"""

_NEW_THIS_RUN_COLS = ["標題", "申請機關", "連結", "疑似舊案", "對應舊案id"]


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


def _dbname(conf):
    """資料庫名稱：環境變數 POSTGRES_DB 優先（驗證時指到測試庫，不碰正式資料），
    沒有才讀 .env——跟 POSTGRES_HOST/PORT 讀環境變數的做法一致。"""
    return os.environ.get("POSTGRES_DB") or conf.get("POSTGRES_DB", "palentir_test_db")


def connect():
    """建立資料庫連線（公開函式，dev_api.py 等其他模組共用同一套連線設定，不重寫）。"""
    conf = _load_env()
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5434")),
        dbname=_dbname(conf),
        user=conf.get("POSTGRES_USER", "admin"),
        password=conf.get("POSTGRES_PASSWORD", ""),
    )


def ensure_pending_table(conn):
    """建立待審表（已存在就什麼都不做）。"""
    with conn.cursor() as cur:
        cur.execute(_PENDING_DDL)


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


def _key(category, source_url):
    return ((category or "").strip(), (source_url or "").strip())


def _host(url):
    """網址的網域（小寫、去掉 www.），疑似舊案比對用。"""
    host = (urlsplit((url or "").strip()).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _backup():
    """寫入前先 pg_dump 備份到本機（沿用 md/DEPLOY_FRONTEND.md 既有的手動慣例指令）。
    備份失敗就丟例外中止——備份是寫入前的必要前提，備份失敗等於沒有安全網，
    不能因為備份失敗就跳過備份直接往下寫。回傳備份檔案路徑。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(DATA_DIR, f"db_backup_{ts}.sql")
    dbname = _dbname(_load_env())
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


def _find_suspected_dup(new_row, known_by_category):
    """跟同機關、同網域的 subsidies 案子比標題相似度，最高分 ≥ TITLE_SIM_TH 回傳舊案 id，否則 None。
    相似度函式/門檻直接重用 postprocess（去重規則用的同一套），不另寫一份。
    延後 import：dev_api.py 也會 import 本模組，不讓它連帶載入整個萃取流程。"""
    from ..postprocess import _sim, TITLE_SIM_TH
    best_id, best = None, 0.0
    host = _host(new_row["source_url"])
    for old_id, old_title, old_host in known_by_category.get((new_row["category"] or "").strip(), []):
        if old_host != host:
            continue
        s = _sim(new_row["title"], old_title)
        if s > best:
            best_id, best = old_id, s
    return best_id if best >= TITLE_SIM_TH else None


def _write_new_this_run(new_rows, path=NEW_THIS_RUN_CSV):
    """本次新增報表（每次覆蓋；沒有新案也寫表頭，不留上次的內容）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(_NEW_THIS_RUN_COLS)
        for m in new_rows:
            dup = m.get("suspected_dup_of")
            w.writerow([m["title"], m["category"], m["source_url"],
                        "是" if dup is not None else "", dup if dup is not None else ""])


def sync_new_to_pending(csv_path, run_at=None):
    """把 csv_path 最終去重結果的成功列跟資料庫比對，只把新案寫進 subsidies_pending。
    run_at：本次執行時間（寫進 first_seen_at，也用來驗證新增筆數），預設現在。
    回傳統計 dict：success_rows / new / skipped_known / suspected_dup / new_rows。"""
    t0 = time.time()
    run_at = (run_at or datetime.datetime.now()).replace(microsecond=0)
    rows = _load_success_rows(csv_path)
    if not rows:
        raise RuntimeError("成功列數為 0，拒絕同步（管線可能異常：全部站點抓取失敗或萃取全失敗）。")
    mapped = [_map_row(r) for r in rows]

    conn = connect()
    try:
        ensure_pending_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT id, category, source_url, title FROM subsidies")
            known = set()
            known_by_category = {}
            for sid, cat, url, title in cur.fetchall():
                known.add(_key(cat, url))
                known_by_category.setdefault((cat or "").strip(), []).append((sid, title, _host(url)))
            cur.execute("SELECT category, source_url FROM subsidies_pending")
            known.update(_key(cat, url) for cat, url in cur.fetchall())

        new_rows, skipped = [], 0
        for m in mapped:
            k = _key(m["category"], m["source_url"])
            if k in known:
                skipped += 1
                continue
            known.add(k)  # 批內重複 key 只取第一筆（postprocess 後理論上不會發生，防呆）
            m["suspected_dup_of"] = _find_suspected_dup(m, known_by_category)
            new_rows.append(m)

        backup_path = None
        if new_rows:
            # 備份在交易外做（pg_dump 是另一個連線），但一定先於任何寫入。
            backup_path = _backup()
            print(f"  已備份：{backup_path}")
            cols = _DB_COLUMNS + ("status", "first_seen_at", "suspected_dup_of")
            insert_sql = (
                "INSERT INTO subsidies_pending (" + ", ".join(cols) + ") "
                "VALUES (" + ", ".join(["%s"] * len(cols)) + ") RETURNING id"
            )
            with conn.cursor() as cur:
                inserted_ids = []
                for m in new_rows:
                    cur.execute(insert_sql, [m[c] for c in _DB_COLUMNS]
                                + ["pending", run_at, m["suspected_dup_of"]])
                    inserted_ids.append(cur.fetchone()[0])
                # 用本次實際拿到的 id 驗證，不用 first_seen_at：時間只到秒，同一秒內跑兩次會算到別次的列。
                cur.execute("SELECT count(*) FROM subsidies_pending WHERE id = ANY(%s)", (inserted_ids,))
                (actual,) = cur.fetchone()
                if actual != len(new_rows):
                    # 不在這裡 rollback：讓例外往下拋，由外層 except 統一處理，避免重複呼叫 rollback()。
                    raise RuntimeError(
                        f"寫入後筆數對不上（預期新增 {len(new_rows)}、資料庫實際 {actual}），已 rollback、資料庫維持執行前狀態。"
                    )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    _write_new_this_run(new_rows)
    stats = {
        "success_rows": len(mapped),
        "new": len(new_rows),
        "skipped_known": skipped,
        "suspected_dup": sum(1 for m in new_rows if m["suspected_dup_of"] is not None),
        "new_rows": [{"title": m["title"], "category": m["category"], "source_url": m["source_url"],
                      "suspected_dup_of": m["suspected_dup_of"]} for m in new_rows],
    }
    elapsed = time.time() - t0
    print(f"  成功列 {stats['success_rows']} 筆：新案 {stats['new']} 筆寫入待審"
          f"（其中疑似舊案 {stats['suspected_dup']} 筆）、已知案跳過 {skipped} 筆"
          f"（耗時 {elapsed:.1f}s{'，備份：' + backup_path if backup_path else '，無新案未備份'}）。")
    print(f"  本次新增報表：{NEW_THIS_RUN_CSV}")
    return stats


def _lock_pending(cur, ids):
    """鎖住指定的待審列，只接受 status=pending；有任何一筆不存在或已審過就拋例外。"""
    ids = sorted(set(int(i) for i in ids))
    if not ids:
        raise ValueError("沒有指定要審核的待審 id。")
    cur.execute("SELECT id FROM subsidies_pending WHERE id = ANY(%s) AND status = 'pending' FOR UPDATE",
                (ids,))
    found = {r[0] for r in cur.fetchall()}
    missing = [i for i in ids if i not in found]
    if missing:
        raise ValueError(f"以下待審 id 不存在或不是 pending（已審過）：{missing}，本次審核未執行。")
    return ids


def approve_pending(ids):
    """核准：把指定待審列寫進 subsidies，並標記 approved＋reviewed_at。單一交易，寫入前備份。
    回傳寫進 subsidies 的筆數。"""
    conn = connect()
    try:
        ensure_pending_table(conn)
        with conn.cursor() as cur:
            ids = _lock_pending(cur, ids)
            _backup()
            cols = ", ".join(_DB_COLUMNS)
            cur.execute(f"INSERT INTO subsidies ({cols}) SELECT {cols} FROM subsidies_pending "
                        "WHERE id = ANY(%s)", (ids,))
            inserted = cur.rowcount
            cur.execute("UPDATE subsidies_pending SET status = 'approved', reviewed_at = %s "
                        "WHERE id = ANY(%s)", (datetime.datetime.now().replace(microsecond=0), ids))
            if inserted != len(ids):
                raise RuntimeError(f"寫入 subsidies 筆數對不上（預期 {len(ids)}、實際 {inserted}），已 rollback。")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return inserted


def reject_pending(ids):
    """退回：標記 rejected＋reviewed_at（不動 subsidies，不需備份）。之後再抓到同 key 也會跳過。
    回傳更新筆數。"""
    conn = connect()
    try:
        ensure_pending_table(conn)
        with conn.cursor() as cur:
            ids = _lock_pending(cur, ids)
            cur.execute("UPDATE subsidies_pending SET status = 'rejected', reviewed_at = %s "
                        "WHERE id = ANY(%s)", (datetime.datetime.now().replace(microsecond=0), ids))
            updated = cur.rowcount
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return updated
