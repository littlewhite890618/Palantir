## Context

- `/new-cases` 路由與 `NewCasesPage.js` 已經存在（N1 建的占位頁），路由條件是 `{LOCAL_API_URL && <Route .../>}`，用一般 import 不做 `NODE_ENV` 排除。這次只換頁面內容，路由與判斷條件不動。
- `notificationService.js` 目前有 `fetchApproved()`、`getLastSeen()`、`markSeen()`、`countUnread()`；localStorage key 是 `palentir_notif_last_seen`。
- `dev_api.py::_fetch_approved()` 目前查 `id, title, category, reviewed_at`，夠算未讀數但不夠畫卡片。
- `SubsidyCard` 是搜尋頁與收藏頁共用的元件，**用 `item.id` 同時做兩件事**：`navigate('/subsidy/' + item.id)` 與 `onToggleFavorite(item.id)`。所以傳進去的物件，`id` 必須是正式表 `subsidies.id`。
- 收藏狀態在 `favoritesService.js`（localStorage 存 id 陣列），`FavoritesPage` 的用法是 `useState(() => getFavoriteIds())` ＋ `toggleFavorite(id)` 回傳新陣列。

## Goals / Non-Goals

**Goals:**
- 使用者從鈴鐺點進來，看到的就是剛才 popover 告知的那批案子，筆數一致。
- 卡片外觀與互動跟搜尋頁完全一致，不另外維護一套樣式。

**Non-Goals:**
- 顯示全部審核通過的歷史紀錄（只顯示最近一批）。
- 篩選、排序、分頁（每批筆數是個位數）。
- 讓這頁在正式站真的有資料（那需要先把 `reviewed_at` 納入加密匯出，屬後續工作）。

## Decisions

### D1：用「前一次已讀時間」決定要顯示哪一批
- 問題：使用者一點鈴鐺，`markSeen()` 就把已讀時間更新成「現在」。等畫面跳到 `/new-cases`，用「未讀」算出來一定是 0 筆，清單會空白。
- 做法：`markSeen()` 在覆蓋前，先把舊值存到另一個 key `palentir_notif_prev_seen`；新增 `getPrevLastSeen()`。清單顯示 `reviewed_at > prevLastSeen` 的案子。
- 為什麼不用其他做法：
  - 「跳頁時用 navigation state 帶過去」→ 重新整理就沒了，直接輸入網址也沒有。
  - 「進清單頁才標記已讀」→ 跟 N1 已定案的「點鈴鐺就算已讀」衝突，使用者確認過的行為不該為了實作方便改掉。
- 邊界情況：
  - 從未讀過（`prevLastSeen` 不存在）→ 視為全部都要顯示，跟鈴鐺首次顯示全部未讀數一致。
  - 未讀為 0 時點鈴鐺 → 現行程式不呼叫 `markSeen()`，所以 `prevLastSeen` 不會被推進，清單仍顯示上一批，不會變空白。

### D2：`_fetch_approved()` 改查完整欄位並 LEFT JOIN 正式表
- 做法：
  ```sql
  SELECT p.*, s.id AS subsidy_id
  FROM subsidies_pending p
  LEFT JOIN subsidies s
    ON s.category = p.category AND s.source_url = p.source_url
  WHERE p.status = 'approved'
  ORDER BY p.reviewed_at DESC, p.id DESC
  ```
- 為什麼用（`category`, `source_url`）比對：這是增量偵測、待審判重、唯一鍵都在用的同一組身分 key（`subsidies_pending` 上就有 `UNIQUE (category, source_url)`），不必另外新增外鍵欄位或改資料表。
- 為什麼不存外鍵：`approve_pending()` 是 `INSERT INTO subsidies ... SELECT ... FROM subsidies_pending`，要存外鍵得改寫成拿 `RETURNING id` 再回寫待審表，動到 Change A/B 已驗證過的交易流程，風險不划算。
- `p.*` 會一併帶出 `status`、`first_seen_at`、`suspected_dup_of` 等欄位，前端用不到但無害，不特別挑欄位以免日後卡片要加欄位又得改 SQL。

### D3：前端把 API 回傳轉成 `SubsidyCard` 吃的形狀
- 做法：`NewCasesPage` 把每筆 `{...row, id: row.subsidy_id}` 後才交給 `SubsidyCard`——因為卡片用 `item.id` 跳詳細頁和記收藏，必須是正式表的 id。
- `subsidy_id` 為空的情況（正式表那筆被刪掉，例如測試過程中手動 restore 過）：不塞給 `SubsidyCard`，改渲染一張不可點的簡化卡片，標註「此案已不在資料庫中」。這樣符合 spec 的「仍可顯示內容，但不導向不存在的詳細頁」，也不用去改 `SubsidyCard` 的內部邏輯。
- 收藏：比照 `FavoritesPage` 的既有寫法（`useState(() => getFavoriteIds())` ＋ `toggleFavorite`），不另外做一套狀態管理。

### D4：維持 `LOCAL_API_URL` 執行時判斷，不用 `NODE_ENV` 排除
- 沿用 N1 的 D5 決定：這頁規劃要跟鈴鐺一起上線給一般使用者，現在用 `NODE_ENV` 排除、之後上線再加回來等於白做兩次。路由條件已經是這樣寫，這次不動。
- 上線前要補的事（不在這次範圍）：把 `reviewed_at`（或等價依據）納入 `export_subsidies`，並讓 `notificationService`／`NewCasesPage` 在沒有本機 API 時改讀靜態資料。

## Risks / Trade-offs

- [使用者清掉瀏覽器資料] → `prevLastSeen` 消失，清單會顯示全部審核通過的案子。跟鈴鐺未讀數重算是同一個性質的限制，不影響資料正確性。
- [同一秒內審核多筆，`reviewed_at` 只到秒] → 邊界上可能有一筆落到下一批。人工逐筆審核的節奏下機率極低，最多是分批顯示，不會遺漏。
- [（category, source_url）比對不到對應正式表資料] → 只在正式表那筆被手動刪除時發生；已用 D3 的簡化卡片處理，不會讓整頁壞掉。
- [`p.*` 把 `status`、`suspected_dup_of` 等內部欄位也回給前端] → 這是只綁本機、無認證的開發用 API，本來就不對外；不額外挑欄位以換取日後少改一處。

## Migration Plan

1. 純前端＋`dev_api.py` 查詢語句調整，不需要資料庫 migration。
2. 這個功能不出現在正式站，不影響 `export_subsidies`／`deploy_palantir` 既有流程。
3. 回滾：revert 程式碼即可；`palantir_notif_prev_seen` 這個 localStorage key 留著也無害。

## Open Questions

無。
