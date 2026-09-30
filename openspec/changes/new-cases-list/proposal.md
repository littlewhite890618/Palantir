## Why

N1（`subsidy-notification-bell`）已經做出通知鈴鐺與未讀徽章，點 popover 會導向 `/new-cases`，但那一頁目前只是「功能開發中」占位內容。PROGRESS.md 的 N2「新案列表查看」就是要把這頁換成真正的清單，讓使用者看到「剛剛通知的那批新案到底是哪些」，並能點進去看完整內容。

## What Changes

- `/new-cases` 從占位頁換成實際清單，重用搜尋頁的 `SubsidyCard` 元件：卡片外觀、點整列進 `/subsidy/:id`、收藏按鈕的行為都跟搜尋頁一致，不另外設計一套。
- **清單內容是「上次通知的那一批」**，不是全部審核通過的歷史。做法是在標記已讀時把「舊的已讀時間」另存一份，清單顯示審核時間晚於它的案子。這樣點鈴鐺跳過來看得到剛才通知的那批、在清單頁重新整理不會變空白、直接輸入網址進來也是看到最近一批。
- `GET /api/approved` 擴充：目前只回 `id`／`title`／`category`／`reviewed_at`（夠算未讀數，不夠顯示卡片），改為回傳完整補助案欄位，並 LEFT JOIN `subsidies` 取得對應的 `subsidies.id` 供卡片連往詳細頁。比對用（`category`, `source_url`）——跟增量偵測、待審判重用的是同一組身分 key。
- 清單為空時顯示「目前沒有新增的補助案」，不顯示空表格或錯誤。
- 上線規劃跟鈴鐺同一套：只用 `LOCAL_API_URL` 做執行時判斷，**刻意不用 `NODE_ENV` 排除**，因為這頁規劃要跟鈴鐺一起上線給一般使用者。

## Capabilities

### New Capabilities
- `new-cases-list`：新案列表頁的行為契約——顯示哪一批案子、卡片與詳細頁的連動、空狀態、只在資料來源可用時存在的限制。

### Modified Capabilities
- `local-review-api`：「已審核通過清單查詢」端點的回傳內容擴充（完整欄位＋對應的正式表 id），排序與唯讀性質不變。
- `subsidy-notification-bell`：「已讀狀態存於本機瀏覽器」需求擴充——標記已讀時同時保留前一次的已讀時間，供新案列表判斷要顯示哪一批。徽章計算方式與已讀時機不變。

## Impact

- **修改**：`subsidy_crawler/dev_api.py`（`_fetch_approved` 改查完整欄位＋JOIN）、`React/src/services/notificationService.js`（`markSeen` 多存前一次時間、新增 `getPrevLastSeen`）、`React/src/pages/NewCasesPage.js`（占位內容換成清單）。
- **沿用不改**：`SubsidyCard`（直接重用）、`favoritesService`（收藏行為）、`App.js` 的 `/new-cases` 路由與判斷條件、鈴鐺元件本身。
- **不影響**：管線、審核頁 `/admin`、匯出與部署流程；正式發布版本的行為不變（`LOCAL_API_URL` 為 null 時路由不註冊）。
- **依賴**：無新增套件。
