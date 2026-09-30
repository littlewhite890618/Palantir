## Why

Change A（`pipeline-incremental-review-queue`）已經讓管線把新案寫進待審表 `subsidies_pending`，但目前只能下 SQL 或呼叫 Python 函式才能審核，沒有可用的介面。路線圖 N1 要「新案經人工審核後才呈現給前端」，審核這一步是整條流程唯一還缺的環節。

線上站是 GitHub Pages 靜態站、不能寫資料庫，而且審核的人只有使用者本人、資料庫也只跑在他自己的機器上，所以審核頁做在**本機開發模式**的前端（`REACT_APP_LOCAL_API_URL` 有設時才存在），透過既有的 `dev_api.py` 寫回資料庫。

## What Changes

- `dev_api.py` 新增三個端點（都只在本機提供）：
  - `GET /api/pending`：待審清單（預設只回 pending），每筆附上疑似舊案的完整內容，供並排比對。
  - `POST /api/pending/approve`、`POST /api/pending/reject`：逐筆審核，直接呼叫既有的 `db.approve_pending`／`db.reject_pending`。
  - `GET /api/run-summary`：回傳 `data/run_summary.json`，讓審核頁顯示「上次執行時間」（排程沒跑就不會有新檔，這是 Change A 已知限制的補償措施）。
- **BREAKING（本機開發）** `dev_api.py` 監聽位址從 `0.0.0.0` 改為 `127.0.0.1`：加上寫入端點後，綁 `0.0.0.0` 等於同網段的人都能改資料庫。瀏覽器跑在本機，改綁本機不影響現有前端。
- 前端新增 `/review` 審核頁與 Navbar 入口，**只在本機開發模式出現**；正式 build（GitHub Pages）完全看不到，也不會呼叫任何寫入端點。
- 審核頁行為：待審案列表（可展開看完整欄位）、逐筆「通過」「退回」按鈕、疑似舊案與新案左右並排比對、操作後清單即時更新、顯示上次管線執行時間。
- 退回不記理由（`subsidies_pending` 不加欄位）。

## Capabilities

### New Capabilities
- `local-review-api`：本機開發 API 的對外行為契約——只綁本機、待審清單（含疑似舊案內容）、逐筆核准／退回、執行摘要查詢、錯誤回報。
- `subsidy-review-ui`：審核頁的可觀察行為——只在本機開發模式存在、待審清單與展開、並排比對、逐筆審核與即時更新、空清單與錯誤呈現、上次執行時間。

### Modified Capabilities
<!-- 無：Change A 的 subsidy-review-queue 契約（新案判定、待審表、審核通過寫入正式表的語意）不變，本次只是加上呼叫它的介面。 -->

## Impact

- **修改**：`subsidy_crawler/dev_api.py`（綁定位址、路由、POST 處理、CORS 允許 POST）、`React/src/App.js`（`/review` 路由）、`React/src/components/Navbar.js`（本機模式才顯示的入口）、`React/src/services/subsidyService.js` 或新增 `reviewService.js`（呼叫新端點）。
- **新增**：`React/src/pages/ReviewPage.js`。
- **沿用不改**：`db.approve_pending`／`db.reject_pending`／`db.connect`（Change A 已驗證）、`PasswordGate` 的本機模式放行邏輯、既有前端樣式慣例（inline style、主色 `#1a73e8`、lucide-react 圖示）。
- **不影響**：管線、`export_subsidies`、`deploy_palantir`、線上站行為。前端鈴鐺與新案列表（N1／N2）屬於下一個 change。
- **依賴**：無新增套件。
