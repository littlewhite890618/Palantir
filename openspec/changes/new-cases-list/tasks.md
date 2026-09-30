## 1. 後端端點擴充（subsidy_crawler/dev_api.py）

- [x] 1.1 `_APPROVED_SQL` 改為 `SELECT p.*, s.id AS subsidy_id`＋`LEFT JOIN subsidies s ON s.category = p.category AND s.source_url = p.source_url`，維持 `WHERE status='approved'`、`ORDER BY reviewed_at DESC, id DESC`（D2）
- [x] 1.2 確認正式表找不到對應資料時 `subsidy_id` 為 null 而非整筆消失（LEFT JOIN 的行為）
- [x] 1.3 更新 docstring 的端點說明：`/api/approved` 現在回完整欄位＋對應正式表 id

## 2. 前端服務層（notificationService.js）

- [x] 2.1 新增 localStorage key `palentir_notif_prev_seen`；`markSeen()` 在覆蓋 `palentir_notif_last_seen` 前先把舊值寫入（D1）
- [x] 2.2 新增 `getPrevLastSeen()`，比照既有 try/catch 寫法；沒有紀錄回 null
- [x] 2.3 新增 `filterLatestBatch(rows)`：回傳 `reviewed_at` 晚於 `getPrevLastSeen()` 的案子；沒有前次紀錄時回全部

## 3. 新案列表頁（NewCasesPage.js）

- [x] 3.1 換掉占位內容：載入時呼叫 `fetchApproved()`，用 `filterLatestBatch` 取出要顯示的那批
- [x] 3.2 載入中／載入失敗兩種狀態（失敗時提示確認 `dev_api.py` 是否啟動，比照 ReviewPage 寫法）
- [x] 3.3 有 `subsidy_id` 的案子：`{...row, id: row.subsidy_id}` 後交給 `SubsidyCard` 渲染（D3）
- [x] 3.4 收藏：比照 `FavoritesPage` 用 `getFavoriteIds()` ＋ `toggleFavorite()`
- [x] 3.5 `subsidy_id` 為 null 的案子：渲染不可點的簡化卡片，標註「此案已不在資料庫中」
- [x] 3.6 空清單顯示「目前沒有新增的補助案」；保留返回按鈕
- [x] 3.7 頁面標題顯示這批的筆數（例如「新增的補助案（3）」）

## 4. 文件

- [x] 4.1 `subsidy_crawler/README.md` 端點一覽：`/api/approved` 說明改為「完整欄位＋對應正式表 id」
- [x] 4.2 `md/PROGRESS.md` 勾選 N2，註明範圍（只列最近一批、卡片重用搜尋頁元件）

## 5. 驗證（本機開發模式，不動正式資料、不發佈）⚠️ 等使用者說可以再執行

- [x] 5.1 `curl /api/approved` 確認回傳完整欄位且每筆有 `subsidy_id`（目前 3 筆皆應對得到正式表）
- [x] 5.2 清空 localStorage → 開 `/new-cases` → 應顯示全部 3 筆（無前次已讀紀錄時顯示全部）
- [x] 5.3 點鈴鐺標記已讀 → 進 `/new-cases` → 仍顯示那 3 筆；重新整理後不變（D1 的核心驗證）
- [x] 5.4 在 `/admin` 通過 1 筆新案 → 點鈴鐺（顯示 1）→ 進清單 → 只顯示那 1 筆，不含先前 3 筆
- [x] 5.5 點卡片 → 正確導向 `/subsidy/:id`，內容與從搜尋頁進入時相同
- [x] 5.6 點收藏 → 收藏頁看得到該筆，狀態一致
- [x] 5.7 手動把某筆的正式表資料刪掉 → 該筆顯示為不可點的簡化卡片，其餘不受影響；驗證後還原
- [x] 5.8 正式模式（不帶 `REACT_APP_LOCAL_API_URL`）→ `/new-cases` 路由不註冊、不發送請求
