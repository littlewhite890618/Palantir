## Context

- 補助案資料由 `getAllSubsidy()`（`services/subsidyService.js`）載入，正式站（加密 JSON）與本機都可用，所以行事曆不需要像通知鈴鐺一樣用 `LOCAL_API_URL` 決定顯示與否。
- deadline 解析目前散在兩處：
  - `SearchResultsPage.js` 的 `parseLatestDeadline()`（2026-09-29 修正版，民國年、多日期取最晚，與後端 `postprocess.py::latest_date()` 同規則）
  - `SubsidyCard.js` 的 `daysUntil()`（自己另一份正則）
- 機關名稱在資料中的欄位是 `category`（SubsidyCard 即以 `item.category` 顯示機關）；計畫名稱是 `title`。
- Navbar 右側目前依序為：資料更新時間、通知鈴鐺（僅本機）、我的收藏、登出。

## Goals / Non-Goals

**Goals:**
- 行事曆與搜尋頁用同一份解析函式，不再新增第三份正則。
- 純前端完成，不動後端、資料表、匯出流程。

**Non-Goals:**
- 不做完整月曆網格（星期欄、空白日期）。
- 不在行事曆加篩選（機關／金額）或搜尋。
- 不改 `SubsidyCard.daysUntil()`（行為不同：它算剩幾天、只取第一個完整日期；統一屬另一個議題）。
- 不記住「返回時重新打開同一個彈窗」；從詳細頁返回時回到行事曆、彈窗關閉。

## Decisions

### 1. 解析函式抽成 `utils/deadline.js`
`DATE_FULL`／`DATE_YM`／`DATE_Y`、`toGregorianYear`、`parseLatestDeadline` 原樣搬過去並 export，`SearchResultsPage` 改 import。`getDeadlineBucket` 留在搜尋頁（只有搜尋頁用）。
- 替代方案：行事曆直接 import SearchResultsPage 的函式 → 頁面互相依賴，不採用。

### 2. 只用 `DATE_FULL` 完整日期的結果才進行事曆
`parseLatestDeadline` 在找不到完整日期時會退回「年月」（當月 1 號）或「只有年」（1/1）。這兩種是推測值，放進行事曆會讓使用者以為真的在 1 號截止。因此 `utils/deadline.js` 另外 export `parseLatestFullDate(s)`：只看 `DATE_FULL`，沒有就回傳 `null` → 依 spec 視為無法解析、不列入。搜尋頁的分桶行為不變（仍用 `parseLatestDeadline`）。
- 替代方案：照用 `parseLatestDeadline` → 「115年6月」會被畫在 6/1，誤導，不採用。

### 3. 資料整理在頁面內一次算完
`CalendarPage` 載入後用 `useMemo` 把資料轉成排好序的有案月份陣列 `[{ monthKey: 'YYYY-MM', days: [...] }]`。資料量約 150–200 筆，不需要快取或分頁。日期 key 用本地時間組字串，避免 `toISOString()` 時區位移造成跨日。

### 3a. 月份切換：只在有案月份陣列裡移動 index
左右箭頭就是在上面的陣列裡 index −1／+1，天然跳過空月份；index 在頭尾時 `disabled`。
- 預設月份：找第一個 `monthKey >= 本月` 的項目；找不到就取陣列最後一個。
- **目前月份放在網址 `?m=YYYY-MM`**（`useSearchParams`，切換用 `replace` 不堆歷史），從詳細頁返回時自然還原，跟搜尋頁把關鍵字放 `?q=` 同一套做法。`?m=` 不在有案月份裡（例如亂打）時退回預設月份。
- 替代方案：sessionStorage → 也可行，但網址較直觀、可分享，且搜尋頁已有前例。

### 4. 彈窗用頁面內 modal（遮罩＋置中卡片）
不用 popover 錨在格子旁：手機寬度下格子小、popover 容易超出畫面。modal 加半透明遮罩，點遮罩、關閉鈕、Esc 都可關閉；清單過長時卡片內部捲動。
- 替代方案：沿用通知鈴鐺的 `.notif-popover` → 定位邏輯不適合格子網格，不採用。

### 5. Navbar 按鈕位置與樣式
行事曆按鈕放在通知鈴鐺之後、「我的收藏」之前，沿用 `navbar-icon-btn` + `nav-icon-label`（窄螢幕自動只留 icon），icon 用 lucide-react 的 `CalendarDays`，位於 `/calendar` 時加 `active`。

### 6. 樣式
日期格子用 CSS grid（`repeat(auto-fill, minmax(…))`），延用現有 CSS 變數（`--paper-raised`、`--rule-strong`、`--seal` 等），不為已過期日期設不同樣式（spec 要求）。

## Risks / Trade-offs

- [只取最晚日期，早梯次的截止日不會出現在行事曆] → 與搜尋頁一致是刻意選擇；spec 已寫明。
- [「115年6月」這類只有年月的 deadline 被排除，行事曆筆數少於搜尋頁「有期限」的筆數] → 實作完成後統計被排除的筆數，列在交付說明中。
- [deadline 欄位裡出現與截止無關的日期（例如公告日）被當成截止日] → 屬資料萃取品質問題，不在本 change 處理。
