# 補助案抓取系統 — 進度追蹤

Palantir 後端（`subsidy_crawler/`）實作進度。權威規格見 [`PALANTIR_SPEC.md`](PALANTIR_SPEC.md)「Palantir 後端規格」。
節奏：**每週約 6 小時**，估計總時程 ~13–15 週（P1 跑通後再校準）。
原則：**完全獨立**——所有程式碼自包含，不 `import` `.claude/skills` 下的檔、不呼叫 skills；需要的既有邏輯一律**複製進專案改路徑**。
用法：任務前的 `- [ ]` 是待辦框，完成就改成 `- [x]` 打勾。

---

## P1 框架 ＋ 三路徑測試（8/5）
> 目標：搭共用底座，並一次證明 requests／render／Selenium 三條抓取路徑都走得通。

- [x] 建專案骨架（`subsidy_crawler/` 結構、`data/`）＋ `requirements.txt`
- [x] 裝瀏覽器環境（Playwright chromium／Selenium chromedriver）
- [x] `common/http.py` — 搬 `LegacyTLSAdapter` + `session`（一般連線）
- [x] `common/year.py` — 民國年判定 ＋ 須知關鍵字放寬
- [x] `common/notice.py` — 須知檔黑白名單 ＋ `find_notice_pdfs`（absolute／links_from／pick_notices）
- [x] `common/store.py` — 寫入 CSV（部門／檔名／連結／抓取時間，以「連結」去重）
- [x] `common/base.py` — adapter 契約（`DEPARTMENT`／`find_notices`／`NEEDS_BROWSER_DOWNLOAD`）＋ `check()` 載入時驗證，run.py 已套用 ✅
- [x] `common/render.py` — Playwright `render_html` ＋ 反偵測 `selenium_fetch`／`selenium_search`／`selenium_download` ✅
- [x] `run.py` — 主入口（`--site`）＋ `http.download`（下載到 pdf_cache、md5 快取）
- [x] `sites/kinmen.py` — 一般連線（requests）跑通【A 型】✅ 端到端：找→下載真PDF→寫CSV
- [x] `sites/tainan.py` — 開瀏覽器 render 跑通【render】✅ 三層導航→下載 3 zip→寫 CSV
- [x] `sites/yunlin.py` — 反偵測 Selenium 跑通【Selenium】✅ 站內搜尋自動發現當年度公告→繞 Cloudflare→瀏覽器下載真PDF→寫CSV（每年自動，免手動更新）
- [x] 三站端到端驗證：`notices.csv` 有金門/臺南/雲林當年度須知列（5列）、`pdf_cache` 有下載檔

## P2 逐站 adapter（8/12）
> 目標：從 P1 三站抽出三種樣板，把剩下的站一站一張小抄接上底座；每批做完逐筆核對。

- [x] 從 P1 抽出三種樣板（requests／render／Selenium）→ `sites/template/template_{requests,render,selenium}.py`
- [x] 批一 · 型態 B 中央靜態站（國發會、數發部、產發署、中小企業署、貿易署、產技司）
- [x] 批二 · 型態 B 直轄市/地方（臺北、桃園、基隆、臺中、苗栗、彰化、嘉義縣、嘉義市）
- [x] 批三 · 型態 A **全數完成**（金門/高雄/臺東/花蓮/新竹市/屏東/南投/澎湖/宜蘭/新竹縣/連江 共11站，宜蘭=Google Drive組合技、連江=站內搜尋POST）
- [x] 共通改進：`year.py` 須知反向排除 `NOTICE_NEG`（附件/範例/範本）；`notice.links_from` 文字空時退用 `title`（南投檔名在 title）；`http.py` 新增 `post()`（連江站內搜尋 POST 表單用）
- [x] 批四 · 型態 C 剩餘（商發署 — render）
- [ ] 每批產出 `(部門,檔名,連結)` CSV ＋ 逐筆人工核對（年度＝當前、無漏抓無誤植）
- [ ] 共通處理：分頁、編碼、連線重試、告警雛形

## P3 萃取入庫（8/17）
> 目標：把抓到的檔案讀出內容、抽時程/金額、存進索引（複製既有引擎進專案，不 import）。

- [ ] 複製 `extract_schedule_amount.py` 進 `common/extract.py`、改路徑（快取改指向專案 data/）
- [ ] 把 P2 各批 CSV 交給 `common/extract.py` 跑萃取（下載＋解析＋抽時程/金額）
- [ ] `common/store.py` 擴充：萃取結果（計畫名/時程/金額/狀態/本地路徑）寫入索引
- [ ] 去重/增量：以「連結」當 key，只處理新的
- [ ] 抽查驗證：3~5 筆時程/金額對照原 PDF
- [ ] 產出「本次新增／更新」清單

## P4 排程 ＋ 監控（8/19）
> 目標：讓它定時自己跑、出事會告警。

- [ ] Python 排程（APScheduler／cron，或掛 n8n 觸發 `run.py`），每日或每週
- [ ] 增量巡檢 ＋「本次新增」報表
- [ ] 告警：某站 0 筆／連續失敗／解析失敗 → email 或 n8n webhook
- [ ] 手動觸發一次 ＋ 模擬某站失敗，確認告警與報表正確

---

## 里程碑
- [x] **M1**：三條抓取路徑證明可行（requests/render/selenium 各一站端到端）✅ 2026-08-05
- [ ] **M2**：可用子集（~15 好抓站）上線，每週自動更新
- [ ] **M3**：28 站全數接入
- [ ] **M4**：排程 ＋ 告警上線，自動化完成
