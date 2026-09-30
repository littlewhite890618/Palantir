## Why

管理員在管理台審核通過的新案，目前只會默默寫進 `subsidies` 表，沒有任何提示告訴使用者「剛剛通過了幾筆」。PROGRESS.md 的 N1「新案上線通知」定義為：審核通過的案子除了合併進正式表，還要出現在搜尋器的通知入口，讓使用者一眼看到新增筆數。這個 change 補上這個入口；點進去看到的實際清單內容留給 N2（下一個 change）。

## What Changes

- 本機開發 API（`dev_api.py`）新增一個唯讀端點，回傳「經審核通過」的清單（每筆含標題、`reviewed_at`），只計入透過管理台審核流程通過的案子——用 `subsidies_pending.status='approved'` 反查，8/22 那批繞過審核流程直接匯入的舊資料天然不會出現。
- 搜尋器 topbar（`Navbar.js`）新增通知鈴鐺圖示，帶未讀數字徽章。未讀數＝`reviewed_at` 比「上次已讀時間」新的筆數。
- 點鈴鐺開啟 popover，顯示「新增了 X 筆補助案」一行文字；同時把目前時間存進瀏覽器 `localStorage` 當「上次已讀時間」（跟收藏功能同一套模式，各自本機獨立，不寫資料庫、不呼叫任何寫入端點），徽章隨即歸零。
- popover 裡那句話可以點擊，導向新路由 `/new-cases`，目前先顯示「功能開發中」占位內容；N2 完成後直接把清單內容接上這個路由，不需要再改連結或這次的程式。
- 通知鈴鐺**只在取得到已審核資料的環境顯示**（用 `LOCAL_API_URL` 執行時判斷），目前等同「只在本機開發模式看得到」。與管理台不同的是，鈴鐺規劃未來要上線給一般使用者，所以**不用 `NODE_ENV` 把程式碼排除在正式產物外**——現在排除，等上線時還要再加回來重驗一次。上線前要補的事（不在這次範圍）：把 `reviewed_at` 納入加密匯出，讓正式站也有判斷依據。

## Capabilities

### New Capabilities
- `subsidy-notification-bell`：通知鈴鐺的行為契約——未讀數如何計算、已讀時機與範圍、popover 內容、點擊導向、只在本機開發模式存在的限制。

### Modified Capabilities
- `local-review-api`：新增一個唯讀端點（已審核通過清單），沿用既有的「只綁本機」「無認證」限制，不動既有的待審清單／核准／退回／執行摘要四個端點。

## Impact

- **修改**：`subsidy_crawler/dev_api.py`（新增 `GET /api/approved` 端點）、`React/src/components/Navbar.js`（鈴鐺圖示＋徽章，只在本機開發模式渲染）、`React/src/App.js`（新增 `/new-cases` 路由，同樣的雙重把關）。
- **新增**：`React/src/services/notificationService.js`（呼叫新端點、比對本機已讀時間）、`React/src/pages/NewCasesPage.js`（N1 階段只做占位內容）。
- **沿用不改**：`subsidy_pending` 資料表結構（不新增欄位）、`db.approve_pending`／`db.reject_pending`（Change A/B 已完成）、審核頁 `/admin`（不受影響）。
- **不影響**：管線、匯出、部署流程；正式發布版本的行為與產物完全不變。
- **依賴**：無新增套件；比照 `localStorage` 收藏功能的既有做法（`favoritesService.js`）。
