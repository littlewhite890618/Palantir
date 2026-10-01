## Why

顧問目前只能在搜尋頁用「期限」篩選粗略分組（30 天內、30–90 天…），沒辦法一眼看出「哪一天有哪些案子截止」。PROGRESS.md 排定 C1 行事曆查看（10/7–10/21），並把原屬 C2 的「點日期查看當日截止案」一起納入，一次交付。

## What Changes

- Navbar（TopBar）新增「行事曆」icon 按鈕，放在通知鈴鐺旁，點擊導向新頁 `/calendar`。
- 新頁 `/calendar`：以「日期格子」呈現補助案截止日。
  - **只列出有補助案截止的日期**，不是完整月曆（沒有案子的日期不出現）。
  - 一次只顯示一個月（標題例如「2026 年 10 月」），標題兩側左右箭頭切換月份；箭頭只在「有案子截止的月份」之間跳，不顯示空月份。
  - 進頁面預設顯示本月；本月沒有案子則顯示之後最近的有案月份（之後都沒有則顯示最晚的有案月份）。
  - 已過與未過的截止日一律顯示，樣式相同，不做顏色區分。
  - 解析不出日期的 deadline（例如「額滿為止」「另行公告」）不出現在行事曆上。
- 點擊日期格子 → 彈出小視窗（popover/modal），列出該日截止的所有補助案，每列只顯示 **id、計畫名稱、機關名稱**；每列整列可點擊，導向既有詳細頁 `/subsidy/:id`。
- 將搜尋頁內的 deadline 解析邏輯（`parseLatestDeadline`）抽到共用 utils，搜尋頁與行事曆共用同一套規則（民國年轉西元、多個日期取最晚）。搜尋頁行為不變。

## Capabilities

### New Capabilities
- `subsidy-deadline-calendar`: 行事曆頁——Navbar 入口、只顯示有截止案的日期格子（一次一個月、左右箭頭切換有案月份）、點日期彈出當日截止案清單（id／計畫名稱／機關，可點進詳細頁）、不可解析日期的排除規則。

### Modified Capabilities
（無。Navbar 只是多一個入口按鈕，通知鈴鐺的需求不變；deadline 解析抽成共用屬實作調整，搜尋頁篩選行為不變。）

## Impact

- 新增：`React/src/pages/CalendarPage.js`、`React/src/utils/deadline.js`（從 SearchResultsPage 搬出解析函式）
- 修改：`React/src/App.js`（加 `/calendar` 路由）、`React/src/components/Navbar.js`（加 icon 按鈕）、`React/src/pages/SearchResultsPage.js`（改 import 共用 utils）、`React/src/App.css`（行事曆與彈窗樣式）
- 資料來源：沿用現有 subsidies 載入方式（加密 JSON／本機 API），不需改後端或資料表。
- `PROGRESS.md`：3.1 C1 與 3.3 C2 合併由本 change 交付。
