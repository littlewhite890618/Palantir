# -*- coding: utf-8 -*-
"""
subsidy_crawler/dev_api.py — 本機開發用：把 subsidies 表用未加密 JSON 供本機前端讀取。

跟正式的「export_subsidies（加密匯出成靜態檔）→ deploy_palantir（發布上線）」是兩條
完全獨立的路徑，只給本機開發時「馬上看到資料庫最新內容」用。deploy_palantir 的
`npm run build` 是在本機直接執行、完全不經過這支程式或 docker-compose 的環境變數，
兩者互不相干，不會有本機開發設定被誤打包進正式發布版本的風險。

用法：
    python -m subsidy_crawler.dev_api
    （預設監聽 0.0.0.0:8001，GET /api/subsidies 回傳目前 subsidies 表全部內容，
    未加密。只給本機/內網開發用，不要在對外開放的機器上執行。
    8001（而非常見的8000）是為了避開本機其他專案常佔用8000的衝突。）
"""
import sys
import io
import json
import datetime
import decimal
from http.server import BaseHTTPRequestHandler, HTTPServer

from .common import db

if hasattr(sys.stdout, "buffer") and (sys.stdout.encoding or "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

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


def _fetch_all():
    conn = db.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM subsidies ORDER BY id")
            cols = [c.name for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


class Handler(BaseHTTPRequestHandler):
    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path != "/api/subsidies":
            self.send_response(404)
            self._cors_headers()
            self.end_headers()
            return
        try:
            rows = _fetch_all()
            body = json.dumps(rows, default=_json_default, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            msg = json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(msg)

    def log_message(self, fmt, *args):
        print(f"[dev_api] {self.address_string()} - {fmt % args}")


def main():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"=== 本機開發用 API：http://localhost:{PORT}/api/subsidies ===")
    print("僅供本機前端開發使用，未加密、不影響正式部署流程。Ctrl+C 結束。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
