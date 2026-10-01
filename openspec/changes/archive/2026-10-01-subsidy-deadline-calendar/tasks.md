## 1. 共用 deadline 解析

- [x] 1.1 新增 `React/src/utils/deadline.js`：從 `SearchResultsPage.js` 原樣搬出 `DATE_FULL`／`DATE_YM`／`DATE_Y`、`toGregorianYear`、`parseLatestDeadline` 並 export
- [x] 1.2 在 `utils/deadline.js` 新增 `parseLatestFullDate(s)`：只看 `DATE_FULL`，取最晚日期，找不到回傳 `null`
- [x] 1.3 `SearchResultsPage.js` 改 import `parseLatestDeadline`，刪掉頁內重複定義；確認搜尋頁「期限」篩選結果與改動前相同

## 2. 行事曆頁

- [x] 2.1 新增 `React/src/pages/CalendarPage.js`：用 `getAllSubsidy()` 載入資料，處理載入中與載入失敗狀態
- [x] 2.2 用 `useMemo` 依 `parseLatestFullDate(item.deadline)` 分組成「月份 → 日期 → 補助案」，日期 key 用本地時間組字串；無法解析的案子略過
- [x] 2.3 渲染：月份由早到晚，每組顯示「YYYY 年 M 月」標題＋日期格子（日期＋「N 件」）；過期與未過期同樣式；沒有任何日期時顯示空狀態文字
- [x] 2.5 改成一次顯示一個月：標題兩側左右箭頭在有案月份陣列中切換（頭尾停用）；預設本月→之後最近有案月份→最晚有案月份；目前月份存 `?m=YYYY-MM`（replace），無效值退回預設
- [x] 2.4 `App.js` 在 `MainLayout` 下加 `/calendar` 路由（不受 `LOCAL_API_URL` 限制）

## 3. 當日清單彈窗

- [x] 3.1 點日期格子開啟置中 modal（半透明遮罩），標題顯示該日期
- [x] 3.2 清單每列顯示 id、計畫名稱（`title`）、機關（`category`），整列可點，導向 `/subsidy/:id`
- [x] 3.3 關閉方式：關閉鈕、點遮罩、按 Esc；清單過長時卡片內部捲動

## 4. Navbar 入口

- [x] 4.1 `Navbar.js` 在通知鈴鐺之後、我的收藏之前加行事曆按鈕（lucide `CalendarDays`、`navbar-icon-btn`＋`nav-icon-label`「行事曆」），位於 `/calendar` 時加 `active`

## 5. 樣式

- [x] 5.1 `App.css` 加行事曆頁（月份標題、日期格子 grid）與 modal 樣式，沿用現有 CSS 變數，深淺色都可讀
- [x] 5.2 手機寬度（約 375px）檢查：格子不溢出、modal 不超出畫面、Navbar 只剩 icon

## 6. 驗證與收尾

- [x] 6.1 `npm start` 實際操作：從 Navbar 進入 → 點日期 → 點清單列進詳細頁 → 返回；用民國年、多梯次、只有年月、純文字四種 deadline 各抽一筆核對位置
- [x] 6.2 統計被排除筆數（無法解析／只有年月）並記在交付說明
- [x] 6.3 更新 `md/PROGRESS.md`（3.1 C1、3.3 C2 標示由本 change 交付）與 `md/PALANTIR_SPEC.md`（新增行事曆頁章節）
