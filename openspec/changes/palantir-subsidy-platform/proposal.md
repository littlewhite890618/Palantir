## Why

Palantir 補助案平台（前端 `React/` 瀏覽站 ＋ 後端 `subsidy_crawler/` 抓取管線）目前開發到一半，
所有設計決策散落在多份 `md/*.md`（`PALANTIR_SPEC.md`、`PROGRESS.md`…），是多輪臨時討論後
定案的結果。導入 OpenSpec，把這些已定案的規則收斂成 spec-driven 的單一真相來源，讓後續
（尤其後端 P2 尾段～P4 的自動化）都以規格為準，避免同一件事反覆重新討論。

## What Changes

- 新增兩個 capability 規格，涵蓋整個平台目前的定案行為：
  - `subsidy-browser`（前端）：HomePage 三維度篩選、瀏覽/搜尋共用分頁、SubsidyCard、收藏（localStorage 過渡）、詳細頁。
  - `subsidy-crawler`（後端）：28 站巡檢、以「公告發布日」判當前年度、adapter 契約、型態 A/B/C、萃取入庫、排程與告警。
- 把 `md/PROGRESS.md` 的 P1–P4 進度轉成本 change 的 `tasks.md`，保留已完成 `[x]` 與待辦 `[ ]` 狀態。
- 把技術選擇理由與風險對策整理進 `design.md`（前端衍生分類/CORS/localStorage；後端完全獨立、環境坑、萃取引擎重用）。
- 這是**記錄既有平台的基準規格**，不改動任何前端或後端既有程式行為（非破壞性）。

## Capabilities

### New Capabilities
- `subsidy-browser`: 前端補助案瀏覽站——依機關/金額/期限篩選、關鍵字搜尋、分頁、卡片顯示、收藏、詳細頁（申請資格/應備資料）。
- `subsidy-crawler`: 後端補助案自動抓取管線——定期巡檢 28 個政府網站，抓當前年度「申請須知」檔、萃取時程/金額、先獨立存放於 CSV 索引。

### Modified Capabilities
<!-- 無：baseline 為空，兩個能力皆為新增。 -->

## Impact

- **前端** `React/`：`HomePage`、`SubsidyCard`、`FavoritesPage`、`SubsidyDetailPage`、`services/favoritesService.js`、`services/subsidyService.js`、`utils/format.js`。資料來源為 `get-all-subsidy` webhook（`SELECT *`）。
- **後端** `subsidy_crawler/`：`common/*`（http/year/notice/store/base/render/extract）、`sites/<slug>.py`×28、`run.py`；輸出 `data/notices.csv` ＋ `pdf_cache`，**不寫 `subsidies` 表**。
- **相依/環境**：政府網站過時 TLS（`LegacyTLSAdapter`）、Playwright/Selenium 瀏覽器、console cp950 與中文檔名限制、既有萃取引擎（複製進專案，不 import skills）。
- **資料**：本 change 純屬規格記錄，不新增/修改 DB 資料表結構，也不改 webhook。
