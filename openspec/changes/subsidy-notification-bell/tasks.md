## 1. 後端端點（subsidy_crawler/dev_api.py）

- [x] 1.1 新增 `_fetch_approved()`：`ensure_pending_table` 後查 `status='approved'` 的記錄（至少含 title、reviewed_at），依 `reviewed_at DESC` 排序（D2）
- [x] 1.2 `GET /api/approved` 掛進既有路由字典，沿用 `_send_json`／`_handle` 錯誤處理；沒有任何 approved 記錄時回空清單而非錯誤
- [x] 1.3 更新模組 docstring 的端點一覽，加上 `/api/approved`

## 2. 前端服務層

- [x] 2.1 新增 `React/src/services/notificationService.js`：`fetchApproved()` 打新端點；`getLastSeen()`／`markSeen()` 讀寫 localStorage key `palentir_notif_last_seen`（比照 `favoritesService.js` 的 try/catch 寫法，D1）
- [x] 2.2 `countUnread(rows)`：算出 `reviewed_at` 晚於 `getLastSeen()` 的筆數；沒有已讀紀錄時視為全部未讀

## 3. 通知鈴鐺（Navbar.js）

- [x] 3.1 `Navbar.js` 內新增 `NotificationBell` 元件：掛載時取清單算未讀數，顯示 lucide-react 鈴鐺圖示（沿用 `navbar-icon-btn` 既有樣式）
- [x] 3.2 未讀數 > 0 時在圖示右上角顯示數字徽章；未讀數為 0 時不顯示徽章
- [x] 3.3 點擊開啟 popover：未讀 > 0 顯示「新增了 X 筆補助案」、未讀為 0 顯示「目前沒有新增的補助案」（D4）
- [x] 3.4 點擊同時呼叫 `markSeen()` 並把未讀數歸零；再次點擊只是開關 popover，不重複寫入
- [x] 3.5 點擊 popover 外部或再次點鈴鐺可關閉 popover
- [x] 3.6 鈴鐺整塊用 `{LOCAL_API_URL && ...}` 包住，正式模式不渲染（D4）
- [x] 3.7 `App.css` 補徽章與 popover 樣式（含手機寬度下 popover 不超出畫面）

## 4. 占位頁與路由

- [x] 4.1 新增 `React/src/pages/NewCasesPage.js`：只顯示「功能開發中」占位內容，不呼叫任何 API
- [x] 4.2 `App.js` 用一般 import 引入 `NewCasesPage`，以 `LOCAL_API_URL` 判斷註冊 `/new-cases` 路由（**不用** `isDev`／`NODE_ENV` 排除，理由見 D3／D5）
- [x] 4.3 popover 的筆數文字連到 `/new-cases`

## 5. 文件

- [x] 5.1 `subsidy_crawler/README.md` 端點一覽表加上 `/api/approved`
- [x] 5.2 `md/PROGRESS.md` 更新 N1 完成範圍；註明清單頁內容屬 N2

## 6. 驗證（本機開發模式，不動正式資料、不發佈）⚠️ 等使用者說可以再執行

- [x] 6.1 `curl /api/approved` 確認回傳目前 3 筆已通過記錄、含 reviewed_at、排序正確
- [x] 6.2 本機前端首次開啟（清空 localStorage）→ 鈴鐺顯示 3；確認 8/22 匯入的 165 筆未被計入
- [x] 6.3 點開鈴鐺 → popover 顯示「新增了 3 筆補助案」、徽章歸零；重新整理後仍為 0
- [x] 6.4 在 `/admin` 再通過 1 筆 → 重新整理搜尋器 → 鈴鐺顯示 1（非 4），確認累積計算正確
- [x] 6.5 未讀為 0 時點鈴鐺 → 顯示「目前沒有新增的補助案」
- [x] 6.6 點 popover 文字 → 導向 `/new-cases` 看到「功能開發中」占位頁
- [x] 6.7 正式模式（不帶 `REACT_APP_LOCAL_API_URL`）啟動前端 → topbar 沒有鈴鐺、未對 `/api/approved` 發出任何請求（看 Network）、console 無錯誤。**不檢查 build 產物有無相關字串**：此功能規劃未來要上線給一般使用者，程式碼允許被打包，與管理台（必須整段排除）的驗證標準不同
