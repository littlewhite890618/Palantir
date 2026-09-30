# -*- coding: utf-8 -*-
"""
subsidy_crawler/dev_api.py — 本機開發用 API：給本機前端讀 subsidies、審核待審新案。

跟正式的「export_subsidies（加密匯出成靜態檔）→ deploy_palantir（發布上線）」是兩條
完全獨立的路徑，只給本機開發時「馬上看到資料庫最新內容」與「審核新案」用。
deploy_palantir 的 `npm run build` 是在本機直接執行、完全不經過這支程式或 docker-compose
的環境變數，兩者互不相干，不會有本機開發設定被誤打包進正式發布版本的風險。

端點：
    GET  /api/subsidies            正式表全部內容（未加密）
    GET  /api/pending              待審新案（status=pending），疑似舊案一併帶出舊案內容
    GET  /api/approved             已審核通過清單（status=approved），供前端通知鈴鐺算未讀數
    GET  /api/run-summary          最近一次管線執行摘要（沒跑過回 {"exists": false}）
    POST /api/pending/approve      {"id": n} 核准 → 寫入正式表、標記 approved
    POST /api/pending/reject       {"id": n} 退回 → 標記 rejected（不寫正式表）

用法：
    python -m subsidy_crawler.dev_api
    （監聽 127.0.0.1:8001。**只綁本機**：本服務沒有任何認證，加上審核寫入端點後，
    綁 0.0.0.0 等於同網段的人都能改資料庫。瀏覽器跑在本機，前端不受影響。
    若真要從別台電腦連（不建議），改 BIND_HOST 為 "0.0.0.0"。
    8001（而非常見的8000）是為了避開本機其他專案常佔用8000的衝突。）
"""
import os
import sys
import io
import json
import datetime
import decimal
from http.server import BaseHTTPRequestHandler, HTTPServer

from .common import db, monitor

if hasattr(sys.stdout, "buffer") and (sys.stdout.encoding or "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BIND_HOST = "127.0.0.1"   # 只綁本機（見模組 docstring）
PORT = 8001
# react docker 服務（docker-compose.yml）跑在這個 origin，只允許它跨源呼叫。
ALLOWED_ORIGIN = "http://localhost:3000"


def _json_default(o):
    """跟 export_subsidies.py 的 json_default 同款處理：日期/時間轉 ISO 字串
    （前端 new Date() 靠這個），Decimal 轉 float。"""
    if isinstance(o, (datetime.datetime, datetime.date, datetime.time)):
        return o.isoformat()
    if isinstance(o, decimal.Decimal):
        return float(o)
    raise TypeError(f"Not JSON serializable: {type(o)!r}")


def _rows(cur):
    cols = [c.name for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _fetch_all():
    conn = db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM subsidies ORDER BY id")
            return _rows(cur)
    finally:
        conn.close()


# 待審清單：一次把疑似舊案的內容也帶出來，前端才能並排比對，不用每筆再打一次 API。
_PENDING_SQL = """
SELECT p.*,
       s.id      AS dup_id,
       s.title   AS dup_title,
       s.category AS dup_category,
       s.amount  AS dup_amount,
       s.deadline AS dup_deadline,
       s.source_url AS dup_source_url
FROM subsidies_pending p
LEFT JOIN subsidies s ON s.id = p.suspected_dup_of
WHERE p.status = 'pending'
ORDER BY p.first_seen_at DESC, p.id
"""
_DUP_KEYS = ("id", "title", "category", "amount", "deadline", "source_url")


def _fetch_pending():
    """待審新案。疑似舊案收成巢狀的 suspected_dup（沒有就是 None）。
    待審表可能還不存在（使用者還沒跑過管線）→ 先確保建表，回空清單而不是 500。"""
    conn = db.connect()
    try:
        db.ensure_pending_table(conn)
        conn.commit()
        with conn.cursor() as cur:
            cur.execute(_PENDING_SQL)
            rows = _rows(cur)
    finally:
        conn.close()
    out = []
    for r in rows:
        dup = {k: r.pop(f"dup_{k}") for k in _DUP_KEYS}
        r["suspected_dup"] = dup if dup["id"] is not None else None
        out.append(r)
    return out


# 已審核通過清單：只回通知鈴鐺算未讀數需要的欄位（標題＋審核時間），不回整列內容。
# 8/22 那批繞過審核流程直接寫進 subsidies 的舊資料，在待審表裡沒有紀錄，天然不會出現在這裡。
_APPROVED_SQL = """
SELECT id, title, category, reviewed_at
FROM subsidies_pending
WHERE status = 'approved'
ORDER BY reviewed_at DESC, id DESC
"""


def _fetch_approved():
    """已審核通過的案子，依審核時間新到舊。純讀取，不改任何狀態。
    待審表可能還不存在（跟 /api/pending 同款防呆）→ 先確保建表，回空清單而不是 500。"""
    conn = db.connect()
    try:
        db.ensure_pending_table(conn)
        conn.commit()
        with conn.cursor() as cur:
            cur.execute(_APPROVED_SQL)
            return _rows(cur)
    finally:
        conn.close()


def _fetch_run_summary():
    """最近一次管線執行摘要；沒跑過（檔案不存在）不算錯誤。"""
    if not os.path.exists(monitor.SUMMARY_PATH):
        return {"exists": False}
    with open(monitor.SUMMARY_PATH, encoding="utf-8") as f:
        return {"exists": True, "summary": json.load(f)}


class Handler(BaseHTTPRequestHandler):
    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status, obj):
        body = json.dumps(obj, default=_json_default, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, fn):
        """統一錯誤處理：ValueError（id 不存在／已審過等使用者錯誤）→ 400，其餘 → 500。"""
        try:
            self._send_json(200, fn())
        except ValueError as e:
            self._send_json(400, {"error": str(e)})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        routes = {
            "/api/subsidies": _fetch_all,
            "/api/pending": _fetch_pending,
            "/api/approved": _fetch_approved,
            "/api/run-summary": _fetch_run_summary,
        }
        fn = routes.get(self.path)
        if fn is None:
            self._send_json(404, {"error": f"找不到端點：{self.path}"})
            return
        self._handle(fn)

    def _body_id(self):
        """讀 POST body 的 id；格式不對就當使用者錯誤（400）。"""
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError) as e:
            raise ValueError(f"request body 不是合法 JSON：{e}") from e
        if not isinstance(data, dict) or not isinstance(data.get("id"), int):
            raise ValueError("request body 需要整數欄位 id，例如 {\"id\": 3}。")
        return data["id"]

    def do_POST(self):
        actions = {
            "/api/pending/approve": (db.approve_pending, "approved"),
            "/api/pending/reject": (db.reject_pending, "rejected"),
        }
        action = actions.get(self.path)
        if action is None:
            self._send_json(404, {"error": f"找不到端點：{self.path}"})
            return
        fn, status = action

        def do():
            pid = self._body_id()
            fn([pid])
            return {"ok": True, "id": pid, "status": status}

        self._handle(do)

    def log_message(self, fmt, *args):
        print(f"[dev_api] {self.address_string()} - {fmt % args}")


def main():
    server = HTTPServer((BIND_HOST, PORT), Handler)
    print(f"=== 本機開發用 API：http://localhost:{PORT}/api/subsidies ===")
    print(f"    待審新案：http://localhost:{PORT}/api/pending（審核頁 /review 用）")
    print(f"    只監聽 {BIND_HOST}，未加密、無認證，僅供本機使用。Ctrl+C 結束。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
