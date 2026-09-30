## 1. 後端 API（subsidy_crawler/dev_api.py）

- [x] 1.1 監聽位址 `0.0.0.0` → `127.0.0.1`，更新模組 docstring 說明原因（加了寫入端點，不可讓同網段改資料庫）
- [x] 1.2 抽共用 `_send_json(status, obj)`；CORS `Allow-Methods` 加 `POST`、允許 `Content-Type` 標頭
- [x] 1.3 `GET /api/pending`：`ensure_pending_table` 後 LEFT JOIN subsidies 取 pending 清單，疑似舊案收成巢狀 `suspected_dup`（無則 null），依 `first_seen_at DESC, id` 排序（D3）
- [x] 1.4 `GET /api/run-summary`：讀 `data/run_summary.json`；檔案不存在回 `{"exists": false}` 而非錯誤
- [x] 1.5 `do_POST` 分派 `/api/pending/approve`、`/api/pending/reject`：取 body 的 `id`，呼叫 `db.approve_pending([id])`／`db.reject_pending([id])`；`ValueError`→400、其他例外→500，body 一律 `{"error": ...}`（D2）
- [x] 1.6 未知路徑維持 404；GET/POST 都要帶 CORS 標頭

## 2. 前端服務層

- [x] 2.1 新增 `React/src/services/reviewService.js`：由 `LOCAL_API_URL` 推導 API base，提供 `fetchPending`／`approve`／`reject`／`fetchRunSummary`，非 2xx 轉成帶後端訊息的 Error（D5）

## 3. 審核頁

- [x] 3.1 新增 `React/src/pages/ReviewPage.js`：載入待審清單與執行摘要；載入中／錯誤／空清單（「目前沒有待審的新案」）三種狀態
- [x] 3.2 列表：標題／申請機關／金額／截止日／第一次抓到時間，點列展開其餘欄位（描述、資格、應備資料、申請方式、諮詢窗口、連結可點開）
- [x] 3.3 疑似舊案：列上紅色標籤；展開後最上方兩欄卡片並排新案 vs 舊案（標題／機關／金額／截止日／連結），值不同的欄位標色；無舊案則不顯示比對區（D6）
- [x] 3.4 逐筆「通過」「退回」按鈕：請求中 disable 該筆、成功後從清單移除並顯示提示、失敗顯示錯誤且保留該筆（D4）
- [x] 3.5 頁面頂端顯示「上次執行：<時間> <結果>」；無紀錄顯示「尚無執行紀錄」
- [x] 3.6 手機寬度下並排改上下堆疊

## 4. 路由與入口（只在本機開發模式）

- [x] 4.1 `App.js`：`LOCAL_API_URL` 有值才註冊 `/review` 路由
- [x] 4.2 `Navbar.js`：同條件才顯示「審核」入口（沿用 lucide-react 圖示與現有樣式）
- [x] 4.3 `ReviewPage` 自身再判斷一次，未設定時顯示「本機開發模式才可使用」，不呼叫任何端點（D1）

## 5. 文件

- [x] 5.1 `subsidy_crawler/README.md`：dev_api 端點一覽、改綁 127.0.0.1 的原因、審核頁怎麼開（dev_api → docker compose up react → localhost:3000 →「審核」）
- [x] 5.2 `md/PROGRESS.md`：N1 底下標註審核頁完成範圍；`md/PALANTIR_SPEC.md` 補審核流程一句話

## 6. 驗證（測試資料庫 `palantir_verify`，不動正式資料）⚠️ 等使用者說可以再執行

- [x] 6.1 建測試庫、複製正式 subsidies，用 `3_extracted_final.csv` 跑一次同步造出 6 筆待審（含 2 筆疑似舊案）
- [x] 6.2 `POSTGRES_DB=palantir_verify` 啟動 dev_api：`curl` 確認 `/api/pending` 回 6 筆、疑似舊案帶出舊案內容；`/api/run-summary` 在無檔案時回 `exists:false`
- [x] 6.3 `curl` 核准 1 筆、退回 1 筆 → 200；重複核准同一筆 → 400 且訊息可讀；正式表不受影響
- [x] 6.4 確認 dev_api 綁本機：`curl http://<本機區網IP>:8001/api/pending` 連不上，`http://127.0.0.1:8001` 正常
- [x] 6.5 前端本機模式實跑（使用者親測，2026-09-24）：管理台 `/#/admin` 看清單、展開、並排比對、通過與退回皆正常；實際審完 6 筆（通過 3／退回 3），正式表 165→168
- [x] 6.6 `npm run build` 後搜尋 build 產物 → 0 命中。過程發現兩件事並修正：① 執行時判斷（LOCAL_API_URL）擋不住打包，改用 `NODE_ENV` 讓壓縮器整段刪除；② `.map` 含完整原始碼且 deploy.py 會推上公開 repo，新增 `React/.env.production` 關閉 source map
- [x] 6.7 確認正式 `palentir_test_db.subsidies` 筆數未變；刪除測試庫與測試產生的檔案

## 7. 改為獨立管理台版面（2026-09-24 追加，D9）

- [x] 7.1 新增 `React/src/components/AdminLayout.js`：管理台標題列（名稱＋目前功能＋回搜尋器連結）＋`Outlet`
- [x] 7.2 `App.js`：搜尋器各頁改掛 `MainLayout`（含 `Navbar`）；審核頁改掛 `/admin` ＋ `AdminLayout`，維持 NODE_ENV／LOCAL_API_URL 雙重把關
- [x] 7.3 `Navbar.js`：移除審核入口（搜尋器不再有任何前往審核頁的連結）
- [x] 7.4 `App.css`：管理台版面樣式（標題列、內容寬度、手機寬度）
- [x] 7.5 文件：README 與 SPEC 的路徑由 `/review` 改為 `/admin`，說明獨立版面
- [x] 7.6 驗證：開發 bundle 內有 `/admin` 與管理台元件、Navbar 已無審核入口；正式 build 解碼後搜尋 9 個關鍵字全部 0 命中（對照組有命中）。⚠️ 關掉 source map 後壓縮檔的中文會被編成 `\uXXXX`，直接 grep 中文一定回 0、會誤判成通過——要先還原跳脫再搜尋
