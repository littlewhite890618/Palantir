## Context

- `subsidies_pending` 已有 `status`（pending/approved/rejected）與 `reviewed_at` 欄位（Change A），`db.approve_pending()` 核准時會設定兩者（Change B 已驗證）。不需要新增欄位。
- `dev_api.py` 目前有 4 個端點（`/api/subsidies`、`/api/pending`、`/api/pending/approve`、`/api/pending/reject`、`/api/run-summary`），共用 `_send_json`／`_handle` 錯誤處理，只綁 `127.0.0.1`（`local-review-api` 主規格已定案）。
- 前端已有兩個「只在本機開發模式存在」的先例可以直接沿用：
  - `App.js` 用 `process.env.NODE_ENV === 'production' ? null : require(...)` 讓正式 build 的壓縮器整段刪除程式碼與字串（`subsidy-review-ui` 已驗證：`REACT_APP_*` 沒設定時不會被打包工具折疊，只有 `NODE_ENV` 會）。
  - 執行時是否真的顯示，再由 `LOCAL_API_URL`（`process.env.REACT_APP_LOCAL_API_URL`）把關。
- `favoritesService.js` 是現成的 localStorage 存取範例：一個 key、JSON 序列化、包 try/catch。通知鈴鐺的「上次已讀時間」用同一種寫法。
- `Navbar.js` 目前右側是「資料更新時間 + 收藏 + 登出」，審核入口已經移除（Change B），鈴鐺要加在收藏左邊或右邊都可以，不影響既有元素。

## Goals / Non-Goals

**Goals:**
- 鈴鐺數字能正確反映「審核流程產生、使用者還沒看過」的新案筆數，且在多次操作、多筆新增之間保持累加正確（不會重複計算、不會漏算）。
- 整個功能只存在於本機開發模式，正式發布版本不受影響。

**Non-Goals:**
- 新案列表頁的實際內容（N2，下一個 change）。
- 任何跨裝置同步已讀狀態的機制。
- 對 `subsidies_pending` 的資料庫寫入或欄位異動。

## Decisions

### D1：未讀比對用「上次已讀時間戳記」而非資料庫旗標
- 做法：`notificationService.js` 讀 `localStorage` 的 `palentir_notif_last_seen`（ISO 字串，沒有就視為 epoch 0，代表「從未讀過」）；跟 API 回傳的 `reviewed_at` 逐筆比對，數出比它新的筆數。
- 為什麼：這是使用者跟我們一起定案的做法（取代原本考慮過的 DB 0/1 開關）。DB 旗標是全域共享狀態，會被任何一次「已讀」動作清空，且要走寫入 API；時間戳記比對純讀取、各裝置獨立，之後如果要延伸到正式站（把 `reviewed_at` 一併匯出），不用改這套邏輯。
- key 命名沿用 `favoritesService.js` 的 `palentir_*` 前綴慣例。

### D2：新端點 `GET /api/approved`，不擴充既有的 `/api/pending`
- 做法：`dev_api.py` 新增 `_fetch_approved()`：`SELECT title, reviewed_at FROM subsidies_pending WHERE status = 'approved' ORDER BY reviewed_at DESC`，走既有的 `_send_json`／`_handle`／路由字典模式，不用新開分支邏輯。
- 為什麼：`/api/pending` 語意是「待審核」，混進已核准的資料會讓審核頁那邊的假設變複雜；分開一個唯讀端點，兩邊互不影響，也對應 spec 裡「本機開發 API」新增的獨立 Requirement。
- 待審表不存在時（極端情況，例如剛換一台全新開發機還沒跑過管線）：沿用 `db.ensure_pending_table` 保證表存在再查，跟 `/api/pending` 一致的防呆方式。

### D3：`/new-cases` 占位頁跟鈴鐺用同一套判斷，一般 import 不做打包排除
- 做法：`App.js` 用一般的 `import NewCasesPage from './pages/NewCasesPage'`，路由註冊條件跟鈴鐺一致（`LOCAL_API_URL` 有值才註冊）。`NewCasesPage.js` 這次只回傳「功能開發中」的靜態內容，不呼叫任何 API。
- 為什麼：這頁是鈴鐺點下去的目的地，鈴鐺以後要上線，它也要跟著上線（見 D5），所以不用 `NODE_ENV` 排除——否則等於現在拿掉、之後再加回來。這跟 `ReviewPage`／`AdminLayout` 用 `isDev ? require(...)` 的作法**刻意不同**，因為那兩個是純內部管理功能。
- N2 銜接方式：之後只要把 `NewCasesPage.js` 內容換成真正的清單邏輯，路由、判斷式、檔案位置都不用動。

### D4：鈴鐺徽章與 popover 放在 `Navbar.js` 內，不獨立成元件
- 做法：`Navbar.js` 內新增一個 `NotificationBell` 函式元件（同檔案），用 `useState` 存未讀數與 popover 開關，`useEffect` 掛載時呼叫 `notificationService.fetchApproved()` 算未讀數。點擊時：開 popover → 呼叫 `notificationService.markSeen()` 寫入時間戳記 → 未讀數歸零（不必重新打 API）。
- 為什麼：目前 `Navbar.js` 的其他圖示（收藏、登出）都是行內邏輯，沒有拆額外元件；鈴鐺邏輯量體差不多，維持同樣的組織方式，不引入新的檔案結構慣例。若之後鈴鐺邏輯明顯變複雜（例如 N2 要共用同一份未讀資料），再抽出。
- 只在有資料來源時渲染：`Navbar.js` 已經 `import { ... LOCAL_API_URL } from '../services/subsidyService'`（Change B 加的），鈴鐺區塊用 `{LOCAL_API_URL && <NotificationBell />}` 包住即可。

### D5：刻意不用 `NODE_ENV` 把鈴鐺排除在正式產物外
- 做法：只用 `LOCAL_API_URL` 做執行時判斷，程式碼照常被打包進正式產物。
- 為什麼：鈴鐺是規劃要給一般使用者（老闆／顧問）看的功能，只是現階段缺正式站的資料來源（`reviewed_at` 還沒隨加密匯出一起出去）才暫時不顯示。若現在用 `NODE_ENV` 整段排除，等要上線時得把程式碼再加回來、再驗證一次，等於白做兩次。
- 跟管理台的差別：`/admin` 審核頁是純內部管理功能，永遠不該出現在公開站，所以用 `NODE_ENV` 讓壓縮器整段刪除（`subsidy-review-ui` D1／D9）。鈴鐺不同，驗證標準因此也不同——驗的是「不顯示、不發請求」，不是「產物裡搜不到」。
- 上線時要補的事（不在這次範圍）：把 `reviewed_at`（或等價的判斷依據）納入 `export_subsidies` 的匯出內容，`notificationService` 改成在沒有本機 API 時改讀靜態資料。

## Risks / Trade-offs

- [使用者清過瀏覽器資料，或換一台電腦，「上次已讀時間」重置為從未讀過] → 未讀數字會把所有歷史審核通過的案子都算進去，可能一次跳出很大的數字。這是 localStorage 方案的既有限制（收藏功能也有同樣性質），可接受；不影響資料正確性，只是通知的呈現會重算一次。
- [`reviewed_at` 只到秒的精度，理論上同一秒審核兩筆會有邊界問題] → 目前是人工逐筆審核，同一秒兩個操作機率可忽略；即使發生，最多是那一筆在下一次比對時才被算進去，不會遺漏或重複計數到看得出來的程度。
- [`/new-cases` 占位頁未來被 N2 取代時，若 URL 或渲染條件變動] → 目前設計刻意讓 N2 只需替換頁面內容、不動路由與判斷式，降低銜接成本。

## Migration Plan

1. 純前端＋`dev_api.py` 新端點，不需要資料庫 migration。
2. 部署：這個功能不出現在正式站，不影響 `export_subsidies`／`deploy_palantir` 既有流程。
3. 回滾：revert 程式碼即可，沒有資料異動需要處理。

## Open Questions

無。
