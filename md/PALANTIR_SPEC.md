# Palantir 前端規格

Palantir 前端（`React/`）規格文件。依 [`DEV_WORKFLOW.md`](DEV_WORKFLOW.md)
的規則：這些都是經過多輪討論定案的「設計型」需求，記錄下來是為了下次要調整規則
時，直接更新這份文件，不用重新討論一次。

## HomePage 篩選規格

## 資料背景

`subsidies` 資料表（`palentir_test_db`）欄位是自由文字，不是結構化的分類/數字/日期，
篩選器的分類規則都是**前端算出來的衍生分類**，不是資料庫裡本來就有的欄位：

- `category`：實際存的是**主辦機關**（36 個不同值，如「經濟部產業發展署」），不是
  「補助類型」。前端把這個欄位標示為「機關」呈現，跟資料庫欄位名不同。
- `amount`：自由文字。改由 `subsidy_crawler` 寫入後，實際格式是「數字+單位」字串（如
  「100萬元」「3000萬元」），不是純數字；另外混著比例字串（如「50%」）、少數特例
  （如「一億」「1億元」這種含「億」字的值）、以及空字串（無金額資訊）。顯示時再一律於
  最前面加「最高」（`utils/format.js` 的 `formatAmount`，純數字才補「萬」，其餘原樣使用）。
  金額篩選（`getAmountBucket`，[HomePage.js](../React/src/pages/HomePage.js)）要取字串
  **開頭的數字部分**做區間判斷，不能直接 `Number(amount)`（帶單位文字會是 `NaN`）——
  這是 2026-08-21 實測發現的真實 bug：126/161 筆因為 `amount` 是「100萬元」這種格式，
  舊版用 `Number()` 直接轉會全部變 `NaN`，金額篩選對它們完全沒作用，已修正。
- `deadline`：37% 是空值，其餘是 `YYYY-MM-DD` 格式，橫跨 2013~2027（很多已經過期）。
- `start_date`：目前 100% 全空，前端沒有任何邏輯依賴這個欄位。

完整欄位（`\d subsidies`）：`id / title / category / amount / start_date / deadline /
description / created_at / source_url / subsidy_timeline / eligibility / required_documents`。
其中 `eligibility`（申請資格）、`required_documents`（應備資料）是為詳細頁新增的 `TEXT`
欄位，目前 217 筆全為 `NULL`，webhook 也還沒回傳（詳見文末「未來規劃：詳細頁」）。

## 篩選規則

**三個維度：機關 / 金額 / 期限。彼此 AND；同一維度內多選彼此 OR。**
空陣列（沒勾選）代表該維度不篩選，不是篩掉所有資料。

### 機關（`category` 欄位）
選項 = 資料中實際出現過的機關名稱，去重後**依筆數從多到少排序**（最常見的機關排最前面）。

### 金額（`amount` 欄位）
| 分類 | 判斷規則 |
|---|---|
| 100萬以下 | 數字 < 100 |
| 100-500萬 | 100 ≤ 數字 < 500 |
| 500-1000萬 | 500 ≤ 數字 < 1000 |
| 1000-3000萬 | 1000 ≤ 數字 < 3000 |
| 3000萬以上 | 3000 ≤ 數字 < 10000 |
| 一億以上 | 數字 ≥ 10000（＝1億），或 `amount` 含「億」字的特例（如「一億」「1億元」） |
| 依比例補助 | `amount` 含 `%` 字元（不轉數字比較） |

判斷順序：含 `%` → 依比例補助；含「億」→ 一億以上；否則取**開頭的數字部分**
（正則 `^(\d+(\.\d+)?)`，例如「100萬元」取「100」）轉數字比對區間。開頭抓不到數字
（含空字串）的值不歸入任何分類（該筆資料在金額維度永遠不會被篩到，但也不會擋掉其他維度）。

### 期限（`deadline` 欄位，比對「今天」動態算）
| 分類 | 判斷規則 |
|---|---|
| 已截止 | `deadline` < 今天 |
| 30天內截止 | 今天 ≤ `deadline` < 今天+30天 |
| 30-90天內截止 | 今天+30天 ≤ `deadline` < 今天+90天 |
| 90天以上（長期） | `deadline` ≥ 今天+90天 |
| 未提供期限 | 空值 |

**設計決定**：已截止的案子刻意保留成可篩選選項，不預設隱藏、不從清單移除。過期資料
要不要繼續顯示是產品層面的決定，不該在篩選器裡默默幫使用者做掉。

## 瀏覽模式 vs 搜尋模式（共用同一套分頁）

`HomePage` 只有一個路由（`/`），原本獨立的「全覽頁」（`/all`、`AllSubsidyPage`）已經
併入這裡並移除；「最新補助案」（依 `start_date` 或資料表順序取前 5 筆的概念）也一併
撤掉，改成下面這套統一邏輯：

- **關鍵字搜尋**只比對 `title`，在「三個篩選維度先縮小範圍」之後的資料裡再比對關鍵字。
- **瀏覽模式**（`searchedKeyword === null`）：顯示篩選後的全部資料，分頁瀏覽。
- **搜尋模式**（`searchedKeyword !== null`）：顯示篩選＋關鍵字後的結果，**一樣分頁**
  （原本搜尋結果是一次全部顯示、不分頁，合併後改成跟瀏覽模式一致，不再有兩套規則）。
- 勾選/取消篩選框、輸入關鍵字搜尋都會立即反映在畫面上，不需要重新按搜尋。
- **頁碼重置**：機關/金額/期限任一篩選維度改變、或搜尋關鍵字改變，頁碼都會自動歸零，
  避免停在一個因為清單變短而不存在的頁碼上。
- 已移除「顯示更多 →」按鈕（原本用來跳去 `/all`，現在全部資料都在同一頁，不需要了）。

## 補助案卡片（SubsidyCard 元件）

`HomePage`、`FavoritesPage` 共用 `components/SubsidyCard.js`，避免重複維護。

### 描述文字（`description` 欄位）

顯示在卡片中間（標題與期限/金額之間），字體 `14px`，**限制 30 字內，超過補「…」**。
完整內容留給詳細頁呈現。空值時該行留白（現況：DB 裡 217 筆 `description` 全部是空的，
webhook 也回傳 `null`，所以目前每張卡片這一行都是空白，要有內容得先在 DB 補資料 +
讓 webhook 回傳）。

### 下載連結（`source_url` 欄位）

`source_url` 8% 是空值，其餘是外部政府網站的直接檔案連結，分散在十幾個不同網域
（PDF/ODT 混雜，部分網址靠查詢參數觸發下載、看不出副檔名）。

**設計決定**：用 `<a href={source_url} target="_blank" rel="noopener noreferrer">` 開新
分頁，不做 `fetch`+blob 的強制下載。原因是這些網址橫跨大量不同網域，前端跨網域抓取
檔案內容大概率會被 CORS 擋下，且會造成「某些連結能下載、某些不行」的不一致行為。
沒有 `source_url` 的資料，下載圖示顯示灰階不可點，並提示「無原始檔案連結」。

### 收藏功能

**設計決定（過渡方案）**：目前專案沒有任何登入/會員機制，收藏功能先用
`services/favoritesService.js` 把資料存在瀏覽器 `localStorage`（key:
`palentir_favorite_ids`，存一組 subsidy id 陣列）。這個服務對外只暴露
`getFavoriteIds()` / `isFavorited(id)` / `toggleFavorite(id)` 三個函式，`SubsidyCard`、
`FavoritesPage` 只依賴這個介面，不直接碰 localStorage。

**未來規劃**：之後會建立簡易登入系統、會員資料表、收藏資料表，讓收藏能跨裝置同步。
屆時只需把 `favoritesService.js` 內部實作換成呼叫後端 API（維持同樣的三個函式介面），
`SubsidyCard`、`FavoritesPage`、`HomePage` 都不用改。這件事還沒排時程，先維持
localStorage 版本。

### FavoritesPage（`/favorites` 收藏頁）

沿用「一次抓全部資料、前端過濾」的既有模式（跟 `HomePage` 一致），不開新的 API 只拿
收藏資料。入口在 `Navbar` 右上角（通知鈴鐺旁邊）的愛心圖示。

## 詳細頁（`/subsidy/:id`，`SubsidyDetailPage`）

**已實作**。點卡片進入單一補助案的詳細頁，上半部「📋 申請資格」（`eligibility`）、
下半部「📎 應備資料」（`required_documents`），另含標題、機關、期限/金額。

設計決策：
- **路由** `/subsidy/:id`，資料來源沿用 `getAllSubsidy()` 抓全部再用 `id` 過濾出該筆
  （跟 `FavoritesPage` 一致，不新增 n8n webhook）。`id` 從 URL 拿到是字串，用
  `String(s.id) === id` 比對。找不到（網址亂打）顯示「找不到這筆補助案」+ 回首頁鈕。
- **點擊行為**：整張卡片可點、跳到詳細頁；卡片上的愛心（收藏）和下載（⬇️）按鈕用
  `e.stopPropagation()` 擋下，不觸發跳頁（`SubsidyCard.js`）。
- **文件式排版**：`eligibility`/`required_documents` 是原始文件裡層次分明的條列
  （`(一)(二)`、`1.2.3.`、`註…`），用 `white-space: pre-wrap` 保留原文換行與縮排、
  配 `line-height: 1.9`，讓它讀起來像一份文件。
- **空值處理**：某些筆這兩個欄位沒有資料時**直接留白**，不顯示佔位文字。

**資料前提**：
1. ✅ `subsidies` 表已新增 `eligibility`（申請資格）、`required_documents`（應備資料）
   兩個 `TEXT` 欄位。命名沿用英文 snake_case 慣例，避免 PostgreSQL 中文欄位名需處處
   加雙引號。使用者已在部分列填入資料（其餘列為 `NULL`，詳細頁對應區塊留白）。
   （另有一個已存在但前端還沒用的 `subsidy_timeline` 欄位，78/217 筆有內容。）
2. ✅（2026-07-26 驗證）`get-all-subsidy` webhook 已回傳含 `description`、`eligibility`、
   `required_documents`、`subsidy_timeline` 的完整欄位（回應為 `SELECT *`，207 筆）。
   因此詳細頁的申請資格/應備資料區塊與卡片描述，只要該列 DB 有值就會顯示，無需再改 webhook。

---

# Palantir 後端規格

Palantir 後端＝補助案自動抓取管線（`subsidy_crawler/`，Python），與前端 `React/` 分離。
目標：定期自動巡檢政府網站，抓「當前年度」補助案的「申請須知」檔案並萃取時程/金額，
**先獨立存放**，未來再決定是否併入 `subsidies` 表。依 [`DEV_WORKFLOW.md`](DEV_WORKFLOW.md)，
以下為多輪討論定案的「設計型」需求，下次要調整規則時直接更新這份文件。

## 目標與範圍

定期巡檢 **28 個**政府網站（7 中央部會＋臺北市＋20 縣市地方型 SBIR；先前口誤稱 34，去重後為 28）。
流程：列表頁 → 篩「公告發布日屬當前年度」→ 進詳情頁找「申請須知類」檔 → 下載 → 萃取時程/金額 → 獨立存放。

## 定案決策（勿隨意更動）

1. **有效期以「公告發布日」判定**：只留發布日屬當前年度者（民國年＝西元−1911；跨年容忍近 3 個月）。
   刻意不採「申請截止日」，因截止日常藏在內文/PDF、解析不穩。
2. **先獨立存放**：輸出到獨立 CSV 索引（`data/notices.csv`）＋原檔快取，**不寫 `subsidies` 表**（避免污染前端資料，
   之後再議是否併入）。
3. **28 站分批建置、逐筆人工核對**（型態 B→A→C，由易到難），過關再下一批。
4. **Python 後端、垂直切片優先、小步共學**（起手站＝金門；P1 同時證明 render〔臺南〕與 Selenium〔雲林〕兩條難路）。
5. **「須知」關鍵字放寬**：申請須知／作業要點／徵件須知／須知／實施計畫／公告事項（不只「申請須知」四字）。
6. **完全獨立（不 import、不呼叫 skills）**：`subsidy_crawler` 所有程式碼自包含；需要的既有邏輯
   （連線／找須知／反偵測／萃取引擎）一律**複製進專案並改路徑**，不 `import` `.claude/skills` 下的檔、
   也不在管線裡呼叫 skills（排程要能無人自動執行）。

## 參考既有程式碼（全部**複製進專案**改寫，不 import、不碰 skills）

| 來源 | 做法 |
|---|---|
| `extract_schedule_amount.py` | 萃取引擎，**複製進 `common/extract.py` 再改路徑**（不 import）。輸入 CSV`(部門,檔案名稱,連結)`，輸出時程6型/金額3型/計畫名；含 NFKC、國字數字、URL 去重、MD5 快取。權威規格見 [`EXTRACT_PDF_SPEC.md`](EXTRACT_PDF_SPEC.md) |
| `LegacyTLSAdapter`＋`session()`＋`HEADERS` | 老政府站過時 TLS／降 SECLEVEL 必需，**複製寫進** `common/http.py` |
| `deep_crawl_find_notice.py` | 參考 `find_notice_pdfs()`＋須知黑白名單，**複製邏輯寫進** `common/notice.py` |
| `spa_render_extract_names.py`（Playwright）、`catch_yunlin/_yunlin.py`（Selenium 反偵測） | 參考其做法，**複製寫進** `common/render.py` |

**環境坑（沿用 `EXTRACT_PDF_SPEC.md`）**：console 為 cp950 → `sys.stdout` 包 utf-8、輸出檔 utf-8-sig；
本環境對**中文檔名 Write 會失敗** → 程式/資料檔名一律英文。

## 套件結構

```
subsidy_crawler/
  common/http.py    # LegacyTLSAdapter + session + Chrome UA
  common/notice.py  # 須知黑白名單 + find_notice_pdfs
  common/year.py    # 民國年判定 + 公告發布日過濾 + 須知關鍵字
  common/store.py   # CSV 索引（notices.csv，以連結去重）+ 沿用 pdf_cache 放原檔
  common/base.py    # SiteAdapter 介面：list_url / filter() / find_notice()
  common/render.py  # 包 Playwright/Selenium（難站用）
  common/extract.py # 複製自既有萃取引擎、改路徑（讀 PDF/DOCX/ODT 抽時程/金額）
  sites/<slug>.py   # 每站一個 adapter（28）
  run.py            # 主入口：--site / --batch
data/notices.csv（＋原檔快取 pdf_cache）
```

## 站點型態與抓取方式（28 站）

三種型態依「**該怎麼抓**」分，不是依網站長相：

- **型態 A（固定下載頁/專區）**：入口 URL 幾乎不變，逐年換檔 → **URL 寫死、選最新民國年的須知檔**。
  通用風險：明年對方可能另開新頁，需「頁面變空/抓不到當年度須知即告警」人工補救。
- **型態 B（每年開新頁、流水號變）**：內頁網址每年換號、猜不到 → **先爬固定的公告列表、篩選條件命中當年那筆，再進詳情找須知檔**。
- **型態 C（特殊）**：擋爬 / SPA，需個別處理（瀏覽器 render 或反偵測）。

### 型態 A（11 站）— 固定下載頁，抓當前年度須知檔

| 機關 | 入口網址 | 抓取方式 |
|---|---|---|
| 高雄市 | `https://kh-sbir.kcg.gov.tw/` | 站內「資料下載」專區 → 挑當前年度「申請須知」 |
| 臺東縣 | `https://taitungsbir.taitung.gov.tw/Index_Download.aspx?mid=19` | 下載專區 → 當前年度須知 |
| 宜蘭縣 | `https://sites.google.com/view/yilansbir/資料下載區` | 資料下載區 → 當前年度須知 |
| 金門縣 ✅已實作 | `https://kinmensbir.org.tw/index.php#section-download` | requests 解析資料下載區 card → 民國年篩當前年度「申請須知」（詳見下方實作步驟） |
| 花蓮縣 | `https://ydc.org.tw/zh-hant/activity/competition/4/` | 頁下方下載清單 → 當前年度須知 PDF |
| 新竹縣 | `https://hchg-sbir.org/` | 首頁最新消息/下載 → 當前年度須知 |
| 新竹市 | `https://www.hccitysbir.org/download/{民國年}` | 下載頁（年度代入 URL）→ 須知。⚠️SSL 需 verify off（`LegacyTLSAdapter` 已解） |
| 屏東縣 | `https://pthg-sbir.nptu.edu.tw/` | 下載專區「{年}計畫文件下載」→ 須知。⚠️連線不穩需重試 |
| 南投縣 | `https://www.nantou.gov.tw/big5/bureau/category_list.php?dptid=376480000au180000&cid=1969` | 進當前年度 SBIR 專區 → 須知 |
| 連江縣 | `https://www.matsu.gov.tw/Chhtml/Download/371030000A/43/` | 產發處下載專區（分類 id=43 固定）→ 篩檔名含 SBIR＋當前民國年 → 須知。⚠️混多主題需精準篩 |
| 澎湖縣 | `https://www.phsbir.com.tw/Home/Downloads` | 專屬 SBIR 站下載頁（固定路由換檔）→ 當前年度須知（舊站 penghu.gov.tw 已棄用） |

### 型態 B（14 站）— 先爬公告列表篩選 → 進詳情找須知檔

| 機關 | 入口網址（列表頁） | 篩選條件 |
|---|---|---|
| 國家發展委員會 | `https://www.ndc.gov.tw/News_TopNews.aspx?n=1CE324F4C0BA40AC` | 「最新資訊」篩**補助資訊**類型 |
| 數位發展部 | `https://digiplus.adi.gov.tw/news_list.html` | 只取**新聞發布**種類 |
| 經濟部產業發展署（`sites/ida.py`，原 `eii.py`，2026-08改名） | `https://eii.nat.gov.tw/tiip/news_list.php?m=1&page=1` | 只取**主題式公告**種類；另擴充6來源（keid cloud/citd、nqa、assist、tmti、tdri，詳見 PROGRESS.md P2.5） |
| 經濟部中小及新創企業署 | `https://www.sme.gov.tw/list-tw-2275?page=1` | 「業務消息」篩含**申請須知**字樣 |
| 國際貿易署 | `https://www.trade.gov.tw/Pages/List.aspx?nodeid=39` | 「公告消息」篩含**申請須知**主題 |
| 經濟部產業技術司 | `https://www.moea.gov.tw/MNS/doit/news/News.aspx?kind=1&menu_id=13419` | 「最新消息」篩含**計畫/申請事項** |
| 臺北市 | `https://www.industry-incentive.taipei/news/1` | 「最新消息」篩含**受理**字樣 |
| 桃園市 | `https://taoyuan-sbir.tw/news` | 「最新消息」篩**公告/受理申請作業** |
| 基隆市 | `https://www.klcg.gov.tw/tw/economy/2627.html` | 「最新公告」篩 **SBIR** |
| 臺中市 | `https://www.economic.taichung.gov.tw/16114/Lpsimplelist` | 「最新消息」篩 **SBIR** |
| 苗栗縣 | `https://www.miaoli.gov.tw/economic_development/News.aspx?n=9707&sms=14729` | SBIR 專區列表 → 詳情須知 |
| 彰化縣 | `https://www.chcg.gov.tw/DTO/greenenergy/06service/service01_con.aspx?topsn=4593` | 「申辦服務」頁（`data_id` 每年變）→ `getFile` 須知 |
| 嘉義縣 | `https://economic.cyhg.gov.tw/News6.aspx?n=441&sms=12508` | 公告列表篩 SBIR → 「計畫簡介」頁附件 |
| 嘉義市 | `https://economic.chiayi.gov.tw/News.aspx?n=4&sms=9000` | 「最新消息」篩 SBIR → 詳情 |

### 型態 C（3 站）— 特殊，需個別處理

| 機關 | 入口網址 | 抓取方式 / 障礙 |
|---|---|---|
| 經濟部商業發展署 | `https://www.aoc.gov.tw/publicList/2` | 「訊息公告」+標題含須知 → 詳情。⚠️403 擋爬，需瀏覽器 render |
| 臺南市 ✅已實作 | `https://www.tainan-sbir.org.tw/list/news` | **SPA（Playwright render）**：文件下載選單→當年度頁→申請階段頁→抓申請文件 zip（詳見下方實作步驟） |
| 雲林縣 ✅已實作 | `https://www.yunlin.gov.tw/News.aspx?n=1244&sms=9662` | **Cloudflare（反偵測 Selenium）**：站內搜尋「地方型SBIR」→當年度公告→詳情→抓公告 PDF；連下載也擋需瀏覽器下載（詳見下方實作步驟） |

> 連江、澎湖原列型態 C（委外/未上架），已找到可用下載頁改列型態 A（見上）；目前 **0 站需人工**。

> **新增第 29 站**（2026-08，`sites/cip.py`）：原住民族委員會（`https://www.cip.gov.tw/`），
> 經濟發展公告分類逐筆進子頁篩「申請須知」PDF，歸型態 B。詳見 PROGRESS.md P2.5。

**P2 建置順序（由易到難）**：型態 B 中央靜態站 → 型態 B 直轄市/地方 → 型態 A（11 站） → 型態 C 需 render/Selenium（商發署·臺南·雲林）。

## 程式樣板（4 種：抓取工具 × 導航層數）

「型態 A/B/C」分的是**網址穩定度／怎麼找到當年度**；但**寫程式**時真正決定「怎麼寫」的是另一條軸——
**用什麼工具抓（requests／render／selenium）× 要導航幾層（一頁／多層）**。實作上只有 4 種樣板，放在 `sites/template/`：

| 樣板 | 工具 × 導航 | 對應站 | 樣板檔 |
|---|---|---|---|
| ① **requests + 一頁** | 一般連線、一頁到位（檔名＝連結文字用 `links_from`；藏它處則自解析 card） | 金門、花蓮、臺東 … | `template_requests.py` ✅ |
| ② **requests + 導航** | 一般連線、多層或「列表→詳情」 | **高雄、南投 ＋ 型態 B 全部（~16 站）** | 待建（以高雄為範例） |
| ③ **render + 導航** | 開瀏覽器 render（SPA）、多層 | 臺南、（商發署待驗） | `template_render.py` ✅ |
| ④ **selenium + 搜尋** | 反偵測繞 Cloudflare、站內搜尋自動發現 | 雲林 | `template_selenium.py` ✅ |

- **② 是 CP 值最高的樣板**：做一個就涵蓋高雄＋南投＋14 個型態 B 站（約 16 站）。高雄/南投不另立小類，歸入②。
- **判斷用哪個樣板**：先問「純 requests 抓不抓得到內容？」（抓不到→③ render 或 ④ selenium）；再問「一頁到位還是要導航？」。
- 三種代表站（金門①／臺南③／雲林④）已實作；② 待以高雄建立。

## P1 已實作三站的實際抓取步驟（金門/臺南/雲林）✅

這三站是 P1 三條路徑的代表（**刻意各挑一條路的代表，非隨機**），實作於 `sites/*.py`，皆**每年自動、免手動更新**。

### 金門 — requests 樣板【型態 A】`sites/kinmen.py`
1. `http.get` 抓固定下載頁 `kinmensbir.org.tw/index.php`。
2. 解析 `#section-download` 區的每張 `.card`：`.txt`＝檔名、`<a>`＝下載連結。
3. `year.has_current_year` ＋ `looks_like_notice` 篩「當前民國年 ＋ 須知類」→ 得「115年金門SBIR申請須知」。
4. `http.download`（requests）下載 PDF。
> 精髓：**固定下載頁 + 民國年自動挑當年度檔**。承辦每年換檔，程式自動跟上，不需改網址。

### 臺南 — render 樣板【SPA / Playwright】`sites/tainan.py`
內容要 JS 才長出來（純 requests 只有空殼），故**每層都 `render.render_html`**：
1. render 入口頁 → 從「文件下載」選單找文字＝當前民國年（「115年」）的連結。
2. render 該年度頁 → 找標題含「申請」的項目（申請階段）連結。
3. render 申請階段頁 → 收 `/upload/*.zip`（個別申請/共同研發/主題式，申請須知包在內），去重。
4. `http.download` 下載 zip。
> 精髓：**SPA 要 render + 多層導航（文件下載→年度→申請階段）到最底層才有檔**。

### 雲林 — selenium 樣板【Cloudflare / 反偵測】`sites/yunlin.py`
縣府站有 Cloudflare，**找連結與下載都要反偵測 Selenium**；且無專屬 SBIR 列表，改用站內搜尋自動發現：
1. `render.selenium_search`：開縣政新聞列表 → 搜尋框打「地方型SBIR」→ 送出。
2. 結果篩「當年度 ＋ SBIR ＋ 補助計畫」→ 當年度公告詳情連結。
3. `render.selenium_fetch` 開詳情頁 → 從「相關檔案」抓 `Download.ashx` 且 `data-name` 含「當年度＋SBIR」的公告 PDF。
4. **連檔案也擋 Cloudflare** → `render.selenium_download` 用瀏覽器下載（adapter 設 `NEEDS_BROWSER_DOWNLOAD=True`，run.py 據此改走瀏覽器下載）。
> 精髓：**反偵測繞 Cloudflare + 站內搜尋自動發現當年度公告 + 連下載都走瀏覽器**。

## 四階段

| 階段 | 內容 | 關鍵檔案 |
|---|---|---|
| **P1 框架＋抓取流程測試** | 抽 `common/*`（含 `common/render.py`）、定義 `base.SiteAdapter`、**金門/臺南/雲林三站各跑通，證明 requests／render／Selenium 三條抓取路徑** | `common/*.py`、`common/render.py`、`sites/kinmen.py`、`sites/tainan.py`、`sites/yunlin.py`、`run.py`、`requirements.txt` |
| **P2 逐站 adapter** | 每站實作：列表URL＋篩選條件＋詳情找須知檔；分批逐筆核對 | `sites/<slug>.py`×28 |
| **P3 萃取入庫** | 各批 CSV 交給專案內 `common/extract.py`（複製自既有引擎、改路徑）跑萃取 → 載入索引 | `common/extract.py`、`common/store.py` |
| **P4 排程＋監控** | APScheduler／cron／n8n 觸發；增量＋「本次新增」報表；**告警**（0 筆/失敗→email 或 n8n webhook） | `run.py`、排程設定 |

## 時程（萃取層已存在，故縮短；依每週工時調整）

P1 ~2 週（含 render/Selenium 三路徑、裝瀏覽器） · P2 ~2.5–3 週（ASP.NET `News.aspx` 站可共用 template） · P3 ~1 週（複製萃取引擎進專案、改路徑、測試） · P4 ~0.5 週
→ **合計 ~5–6 週**；可用子集（~15 好抓站）~2.5–3 週。全 28 站均納入自動化（連江、澎湖已找到可用下載頁）。

## 驗證

- P1：`python -m subsidy_crawler.run --site kinmen` → `data/notices.csv` 出現金門當前年度須知列、`pdf_cache` 有檔。
- P2 每批：`--batch <批>` → 逐筆核對機關/計畫名/公告日/須知連結、年度＝當前、無漏抓無誤植。
- P3：抽查 3–5 筆時程/金額對照原 PDF。
- P4：手動觸發＋模擬某站失敗 → 確認告警與增量報表。

---



