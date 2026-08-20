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

## P2.5 擴充抓取來源（8/13，OpenSpec change `expand-crawler-agency-sources`）
> 目標：人工核對後發現部分機關還有其他官網/計畫頁放當年度須知，逐站補來源；新增1站。

- [x] `sme.py` — 加 SBIR 官網（sbir.org.tw/sbir/dw_apply）來源；固定頁逐年換檔，自動跟上年度
- [x] `eii.py` **改名為 `ida.py`**（`run.py` 匯入與 `SITES` key 同步改，`--site ida`）— 加 6 個來源：
      產發局 keid cloud/citd 兩系統各兩計畫、nqa、assist、tmti、tdri IDDI（互動 render 點「參考文件」，
      115已截止暫回0筆，明年新一期自動抓）
- [x] `doit.py` — A+ 企業創新研發淬鍊計畫「計畫類型」動態收集全部子計畫「資料下載」頁申請須知
- [x] `taoyuan.py` — 加經發局 edb（ASP.NET postback 搜尋「公告」→ 子頁申請須知）
- [x] `kaohsiung.py` — 加經發局 edbkcg（列表含「公告」主題 → 子頁「補助計畫」PDF）
- [x] `aoc.py` — 加 taaa 逐筆進子頁篩「申請須知」（目前該站無補助公告，邏輯保留回0筆）
- [x] `taipei.py` — 加產業局 doed 頁面（常設計畫，不篩年度）
- [x] **新增 `sites/cip.py`**（原住民族委員會）並註冊進 `run.py`
- [ ] **moea.py 放棄**：經濟部補助計畫入口網（service.moea.gov.tw/EE502）結構已探明——
      Cloudflare SPA，計畫卡片 `.content_block` 開 modal，「相關文件下載」分頁內為表單 POST
      下載（`/Plan/DownSiteFile`，需真的點按鈕），列表另有 JS 分頁（1/2/3，共25筆混多年度）。
      不建立 adapter，供之後若重啟參考。
- [x] 29 站全數載入通過 `base.check()` 契約驗證；6 個快站(requests/搜尋型)整合測試通過，
      2 個 Selenium 站(`ida`/`doit`)整合測試進行中

## P3 萃取入庫（8/17）
> 目標：把抓到的檔案讀出內容、抽時程/金額、存進索引（複製既有引擎進專案，不 import）。

- [ ] 複製 `extract_schedule_amount.py` 進 `common/extract.py`、改路徑（快取改指向專案 data/）
- [ ] 把 P2 各批 CSV 交給 `common/extract.py` 跑萃取（下載＋解析＋抽時程/金額）
- [ ] `common/store.py` 擴充：萃取結果（計畫名/時程/金額/狀態/本地路徑）寫入索引
- [ ] 去重/增量：以「連結」當 key，只處理新的
- [ ] 抽查驗證：3~5 筆時程/金額對照原 PDF
- [ ] 產出「本次新增／更新」清單

## P3.5 補助須知 9 欄 LLM 結構化萃取（8/19，OpenSpec change `subsidy-notice-field-extraction`）
> 目標：把 P3 從「時程/金額 2 欄純規則」擴為「LLM 抽 9 欄結構化」。輸出獨立 `data/fields_extracted.csv`，不動 year_check。

- [x] 9 欄：標題(計畫名)/描述/申請機關/申請資格/補助金額上限/補助比例/申請截止日期/應備資料/申請方式/諮詢窗口（行業類別移除）
- [x] `common/textio.py` — 文字層（由 extract_schedule_amount 搬入複製）＋ `extract_docx` 修合併儲存格 bug ＋ `download_via_browser`（403 自動 Selenium 繞 Cloudflare、一般化自 catch_yunlin）
- [x] `common/llm.py` — 多供應商 LLM 客戶端（Gemini 主/OpenRouter 備）＋節流/退避重試/收斂輪替/截斷偵測/JSON 完整性；SYS_PROMPT＋各機關 hint
- [x] `extract_fields.py` — 主流程：讀 CSV→去重→抽字→LLM→申請機關 deterministic 對映(`agency_of`)→寫 CSV；`load_done` 只跳成功列（可續傳）
- [x] 模型校準：`gemini-3.6-flash` 免費 RPD 僅 20 不可用 → 主 `gemini-3.5-flash-lite`＋備 `gemini-3.1-flash-lite`（RPD 各 500）；~10–20s/份
- [x] 全量：newnotices3.csv 去重 182 → **萃取成功 181/182**（桃園已補：換新來源 `invest.tycg.gov.tw/cp.aspx?n=848` 當年度 PDF；剩彰化 getFile 連結失效）
- [x] **`postprocess.py` 後處理去重（8/20）**：類型A正規化(標題去空白標點/截止日標準化)＋規則1-4(標題/金額/截止)＋**規則5類型B**(同金額+標題包含+應備相似≥0.75，併同計畫不同標題)＋**申請類別守門**(個別/共同、單店/多店…不併)。篩選(金額+截止皆空)改 `--drop-empty` 選項、**預設關閉全數保留**。萃取181 → **去重後 156**（155成功+1失敗）。備份 `data/fields_raw181.csv`
- [x] 交付：CSV `data/fields_extracted.csv`（15 欄）＋ 3 個可搜尋網頁（原始182/去重後156/被移除26，Artifact 同連結可更新）
- [ ] 剩餘：彰化重找連結；`requirements.txt`/README 補 `GEMINI_API_KEY` 前提；eii 契約範本應備資料、AI中央廚房金額抽錯(類型C)人工複核

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
