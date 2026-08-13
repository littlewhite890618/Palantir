## 1. 前端補助案瀏覽站（subsidy-browser，已完成）

- [x] 1.1 HomePage 三維度篩選（機關/金額/期限，跨維度 AND、同維度 OR）
- [x] 1.2 機關選項依筆數由多到少排序
- [x] 1.3 金額 7 分類、期限動態 5 分類（已截止保留為可篩選）
- [x] 1.4 瀏覽/搜尋共用分頁（搜尋只比對 title、篩選/關鍵字改變頁碼歸零）
- [x] 1.5 SubsidyCard（描述 30 字截斷、金額「最高 X萬」格式、缺連結停用下載）
- [x] 1.6 收藏功能（favoritesService localStorage 過渡、FavoritesPage）
- [x] 1.7 詳細頁 `/subsidy/:id`（申請資格/應備資料、找不到處理、卡片按鈕不跳頁）

## 2. P1 框架 ＋ 三路徑測試

- [x] 2.1 建專案骨架（`subsidy_crawler/` 結構、`data/`）＋ `requirements.txt`
- [x] 2.2 裝瀏覽器環境（Playwright chromium／Selenium chromedriver）
- [x] 2.3 `common/http.py` — `LegacyTLSAdapter` + `session`（一般連線）
- [x] 2.4 `common/year.py` — 民國年判定 ＋ 須知關鍵字放寬
- [x] 2.5 `common/notice.py` — 須知黑白名單 ＋ `find_notice_pdfs`（absolute/links_from/pick_notices）
- [x] 2.6 `common/store.py` — 寫入 CSV（部門/檔名/連結/抓取時間，以連結去重）
- [x] 2.7 `common/base.py` — adapter 契約（`DEPARTMENT`/`find_notices`/`NEEDS_BROWSER_DOWNLOAD`）＋載入時 `check()`
- [x] 2.8 `common/render.py` — Playwright `render_html` ＋ 反偵測 `selenium_fetch`/`selenium_search`/`selenium_download`
- [x] 2.9 `run.py` — 主入口（`--site`）＋ `http.download`（pdf_cache、md5 快取）
- [x] 2.10 `sites/kinmen.py` — requests 樣板【型態 A】端到端跑通
- [x] 2.11 `sites/tainan.py` — render 樣板【SPA】三層導航跑通
- [x] 2.12 `sites/yunlin.py` — 反偵測 Selenium 樣板【Cloudflare】跑通
- [x] 2.13 三站端到端驗證（notices.csv 有金門/臺南/雲林當年度須知列、pdf_cache 有檔）

## 3. P2 逐站 adapter

- [x] 3.1 從 P1 抽出三種樣板 → `sites/template/template_{requests,render,selenium}.py`
- [x] 3.2 批一 · 型態 B 中央靜態站（國發會、數發部、產發署、中小企業署、貿易署、產技司）
- [x] 3.3 批二 · 型態 B 直轄市/地方（臺北、桃園、基隆、臺中、苗栗、彰化、嘉義縣、嘉義市）
- [x] 3.4 批三 · 型態 A 全數（金門/高雄/臺東/花蓮/新竹市/屏東/南投/澎湖/宜蘭/新竹縣/連江，11 站）
- [x] 3.5 共通改進（year `NOTICE_NEG` 反向排除、notice 文字空退用 title、http 新增 `post()`）
- [x] 3.6 批四 · 型態 C 剩餘（商發署 render）
- [ ] 3.7 每批產出 `(部門,檔名,連結)` CSV ＋ 逐筆人工核對（年度＝當前、無漏抓無誤植）
- [ ] 3.8 共通處理：分頁、編碼、連線重試、告警雛形（連線重試已補；分頁維持現狀；編碼縮小範圍待做；告警併入 P4）

## 4. P3 萃取入庫

- [ ] 4.1 複製 `extract_schedule_amount.py` 進 `common/extract.py`、改路徑（快取指向專案 data/）
- [ ] 4.2 把 P2 各批 CSV 交給 `common/extract.py` 跑萃取（下載＋解析＋抽時程/金額）
- [ ] 4.3 `common/store.py` 擴充：萃取結果（計畫名/時程/金額/狀態/本地路徑）寫入索引
- [ ] 4.4 去重/增量：以「連結」為 key，只處理新的
- [ ] 4.5 抽查驗證：3~5 筆時程/金額對照原 PDF
- [ ] 4.6 產出「本次新增/更新」清單

## 5. P4 排程 ＋ 監控

- [ ] 5.1 Python 排程（APScheduler／cron，或掛 n8n 觸發 `run.py`），每日或每週
- [ ] 5.2 增量巡檢 ＋「本次新增」報表
- [ ] 5.3 告警：某站 0 筆／連續失敗／解析失敗 → email 或 n8n webhook
- [ ] 5.4 手動觸發一次 ＋ 模擬某站失敗，確認告警與報表正確

## 6. 里程碑

- [x] 6.1 M1：三條抓取路徑證明可行（requests/render/selenium 各一站端到端，2026-08-05）
- [ ] 6.2 M2：可用子集（~15 好抓站）上線，每週自動更新
- [ ] 6.3 M3：28 站全數接入
- [ ] 6.4 M4：排程 ＋ 告警上線，自動化完成
