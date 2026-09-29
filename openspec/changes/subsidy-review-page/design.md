## Context

- `dev_api.py` 目前是標準庫 `BaseHTTPRequestHandler`，只有 `GET /api/subsidies`，綁 `0.0.0.0:8001`，CORS 只允許 `http://localhost:3000`。連線設定共用 `db.connect()`。
- Change A 已提供 `db.approve_pending(ids)`／`db.reject_pending(ids)`（單一交易、只接受 pending、核准前備份），以及 `data/run_summary.json`。審核邏輯不必在這個 change 重寫。
- 前端是 React 18＋HashRouter（GitHub Pages 無後端），純 CSS、多為 inline style，主色 `#1a73e8`，圖示用 lucide-react。路由在 `App.js`，`PasswordGate` 包住整個 app。
- `subsidyService.js` 已有 `LOCAL_API_URL = process.env.REACT_APP_LOCAL_API_URL || null`；`PasswordGate` 在 `LOCAL_API_URL` 有值時直接放行（`PasswordGate.js:58`）。這個變數只有 docker-compose 的 react 服務會設，`deploy_palantir` 的 `npm run build` 不吃它——正式版本天生就沒有本機模式。
- React 跑在 docker container，但呼叫 API 的是本機瀏覽器，所以 `dev_api` 改綁 `127.0.0.1` 不影響現有前端。

## Goals / Non-Goals

**Goals:**
- 讓使用者在本機瀏覽器就能看完新案、判斷重複、通過或退回，不必下 SQL。
- 審核入口與寫入端點都不可能出現在公開版本或區域網路上。

**Non-Goals:**
- 前端鈴鐺、新案列表頁、export 只輸出已審核（N1／N2，下一個 change）。
- 帳號系統與權限分級、編輯待審內容、退回理由、批次審核。

## Decisions

### D1：審核頁的存在條件綁在 `LOCAL_API_URL`，不另外做開關
- 做法：`App.js` 用 `process.env.NODE_ENV`（打包時折疊）決定要不要把 `ReviewPage` 打包進來，再用 `LOCAL_API_URL` 決定要不要註冊 `/admin` 路由；`ReviewPage` 自己再判斷一次，沒有就顯示「本機開發模式才可使用」。
- 為什麼：這是現成、已驗證的分界（`PasswordGate` 用同一個變數），正式 build 不會帶入這個變數，等於從根本上不可能誤把審核頁發布出去。三層各自判斷是為了「直接輸入網址」也擋得住。

### D2：API 路由用既有的 `BaseHTTPRequestHandler` 手寫分派，不引入框架
- 做法：`do_GET` 依 `self.path` 分派 `/api/subsidies`、`/api/pending`、`/api/run-summary`；新增 `do_POST` 處理 `/api/pending/approve`、`/api/pending/reject`（讀 `Content-Length`、`json.loads`、取 `id`）。共用一個 `_send_json(status, obj)`。CORS 的 `Allow-Methods` 加上 `POST`，並允許 `Content-Type` 標頭。
- 為什麼：只有 5 個端點、只在本機跑，引入 Flask/FastAPI 會多一個依賴與啟動方式，不划算。
- 錯誤處理：`db` 拋 `ValueError`（id 不存在／已審過）→ 400；其他例外 → 500，body 一律 `{"error": "訊息"}`。

### D3：待審清單一次把疑似舊案的內容帶出來
- 做法：`SELECT ... FROM subsidies_pending p LEFT JOIN subsidies s ON s.id = p.suspected_dup_of WHERE p.status = 'pending' ORDER BY p.first_seen_at DESC, p.id`，舊案欄位在 JSON 裡收成巢狀的 `suspected_dup` 物件（沒有就是 null）。
- 為什麼：前端並排比對需要舊案內容；一次查完可避免前端再對每筆打一次 API。
- `subsidies_pending` 可能還不存在（使用者尚未跑過管線）→ 先 `db.ensure_pending_table(conn)`，回空清單而不是 500。

### D4：審核成功後前端只移除該筆，不重新抓整份清單
- 做法：`ReviewPage` 用 `useState` 存清單，成功後 `setRows(rows.filter(...))`，並顯示短暫的成功提示；按鈕在請求進行中 disable（用 `busyId` 狀態）。
- 為什麼：只有一個人在審，沒有並行衝突；少一次往返，操作更即時。失敗時不動清單，讓使用者重試。

### D5：呼叫 API 的程式放新檔 `React/src/services/reviewService.js`
- 做法：`fetchPending()`、`approve(id)`、`reject(id)`、`fetchRunSummary()`，各自把非 2xx 回應轉成帶訊息的 Error。`API_BASE` 從 `LOCAL_API_URL` 推導（把結尾的 `/api/subsidies` 去掉）。
- 為什麼：`subsidyService.js` 專責「加密靜態檔／本機唯讀資料」那條路徑，審核是只在本機存在的另一件事，分開比較清楚。

### D6：版面沿用既有慣例，比對區用兩欄卡片
- 列表每列顯示標題／申請機關／金額／截止日／第一次抓到時間，點列展開其餘欄位（沿用顧問工作台定案的「可展開列表格」）。
- 疑似舊案：列上顯示紅色「疑似舊案」標籤；展開後在最上方放兩欄卡片，左「本次新案」右「資料庫既有案（id）」，逐欄對齊標題／機關／金額／截止日／連結，值不同的欄位標色。
- 上次執行時間放頁面頂端一行（例如「上次執行：2026-09-22 03:44 成功」）。
- 手機寬度下兩欄改成上下堆疊（沿用現有 RWD 做法）。

### D9：審核頁改為獨立管理台版面 `/admin`（2026-09-24 調整）
- 做法：路由 `/admin` 套 `AdminLayout`（自己的深色標題列：管理台名稱＋目前功能＋回搜尋器連結），搜尋器各頁改由 `MainLayout` 提供 `Navbar`，兩者用 react-router 的巢狀路由＋`Outlet` 分開；`Navbar` 不再有審核入口。
- 為什麼：審核是後台工作、跟給顧問看的搜尋器是兩種使用情境，共用導覽列會讓搜尋器出現只有自己看得懂的入口。獨立版面後，搜尋器完全不知道審核頁的存在。
- 考慮過但不採用：另開一個 React 專案（要維護兩套依賴與啟動流程，目前只有一頁後台，不划算）；由 dev_api 直接吐 HTML（樣式與元件要另寫一套）。

## Risks / Trade-offs

- [改綁 `127.0.0.1` 後，若使用者原本習慣從別台電腦連本機 API] → 目前只有他本人在本機使用；README 會註明改綁原因與如何暫時改回。
- [`dev_api` 沒有任何認證] → 綁本機後，能打到它的人已經能直接操作這台機器上的資料庫，再加 token 只是形式。README 保留「不要在對外開放的機器上執行」的警語。
- [核准疑似舊案會讓正式表出現內容相近的兩筆] → 這是人工判斷的結果，程式不阻擋；並排比對就是為了降低誤判。驗證時會確認核准後的實際結果。
- [待審筆數很多時一次全載入] → 目前每次新案是個位數，不做分頁；若日後變多再加。

## Migration Plan

1. 這個 change 只改本機開發路徑，正式站不受影響，不需要資料庫 migration。
2. 使用者端流程：`python -m subsidy_crawler.dev_api` → `docker compose up react` → 開 `localhost:3000/#/admin`。
3. 回滾：revert 程式即可；待審表與正式表的資料都不會因為回滾而改變。

## Open Questions

- 待審清單之後要不要也能看已審核／已退回的紀錄（加狀態篩選）？目前只列 pending，等實際用過再決定，不影響現有 spec。
