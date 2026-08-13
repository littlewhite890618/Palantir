## Context

動機見 [proposal.md](proposal.md) - Why。此處只記錄影響技術選擇的現狀與約束。

平台為雙軌架構：前端 `React/` 是純前端 SPA（資料來自 `get-all-subsidy` webhook 的 `SELECT *`，
無自有後端 API）；後端 `subsidy_crawler/` 是獨立 Python 巡檢管線，與前端分離、輸出自有 CSV。

既有約束（皆已在實作中處理）：
- `subsidies` 表欄位是**自由文字**，非結構化分類/數字/日期（`category` 實為主辦機關、`amount` 混數字與比例字串、`deadline` 37% 空值且橫跨 2013~2027）。
- 政府網站大量使用**過時 TLS**，Python 預設安全等級連不上。
- 部分站點擋爬（Cloudflare）或為 SPA，純 requests 抓到空殼。
- 本機 console 為 **cp950**（印中文會 `UnicodeEncodeError`）、且**中文檔名 Write 會失敗**。

## Goals / Non-Goals

**Goals:**
- 記錄前後端各項技術選擇的理由與被否決的替代方案，供日後調整時不必重新討論。
- 標明已知風險與對應處理方式（尤其自動化排程後無人值守的場景）。

**Non-Goals:**
- 不改動任何既有前端/後端程式行為（本 change 屬規格記錄）。
- 前端不做登入/會員（收藏維持 localStorage 過渡方案）。
- 後端不寫 `subsidies` 表（先獨立存放，之後再議是否併入）。

## Decisions

### 1. 前端篩選分類在前端算，不改 DB 欄位
`amount`/`category`/`deadline` 是自由文字，篩選用的金額區間、機關清單、期限桶都由前端衍生計算。
**替代方案**：在 DB 端加結構化欄位或視圖。**不選的原因**：資料由 webhook `SELECT *` 提供、
且欄位語意不穩（如 `amount` 有「一億」這種字串特例），前端算可即時調整規則、不必動資料表與 webhook。

### 2. 原始檔下載用 `<a href target="_blank">`，不做 fetch+blob
**替代方案**：前端 `fetch` 檔案內容再觸發下載。**不選的原因**：`source_url` 橫跨十幾個政府網域，
跨網域抓檔大機率被 CORS 擋，且會造成「某些連結能下載、某些不行」的不一致；直接開新分頁最穩定。

### 3. 收藏用 localStorage，隔在單一服務介面後
以 `favoritesService`（`getFavoriteIds`/`isFavorited`/`toggleFavorite`）封裝，卡片/收藏頁只依賴介面。
**替代方案**：直接在元件內讀寫 localStorage。**不選的原因**：未來要換成後端會員 API 時，只需替換服務內部實作，
`SubsidyCard`/`FavoritesPage`/`HomePage` 皆不用改。

### 4. 後端站點型態 A/B/C × 4 種程式樣板
「型態 A/B/C」分的是**網址穩定度/怎麼找到當年度**；實際**寫程式**用 4 種樣板（requests一頁 / requests導航 /
render導航 / selenium搜尋）。**替代方案**：每站各寫一套。**不選的原因**：`requests+導航`一個樣板即涵蓋高雄+南投+
14 個型態 B 站（~16 站），CP 值最高；三條難路（render/selenium）各以代表站（臺南/雲林）先驗證。

### 5. 完全獨立：複製既有邏輯進專案，不 import / 不呼叫 skills
連線（`LegacyTLSAdapter`）、找須知、反偵測、萃取引擎一律**複製寫進 `common/*`** 並改路徑。
**替代方案**：`import` `.claude/skills` 下的現成腳本。**不選的原因**：排程要能無人自動執行，
不能相依於 Claude/skills 環境；複製進專案雖有重複，但換得可獨立部署。

### 6. 以「公告發布日」判當前年度，不用「申請截止日」
**替代方案**：用截止日判年度。**不選的原因**：截止日常藏在內文/PDF、解析不穩；公告發布日在列表頁即可取得、
較可靠（民國年＝西元−1911，跨年容忍近 3 個月）。此決策亦呼應本次資料驗證的發現（見風險）。

### 7. 連線重試用 urllib3 `Retry` 掛在既有 `LegacyTLSAdapter`
全 28 站共用同一個 `Session`，故重試政策集中設定即可（total=3、backoff 1/2/4s、只重試 502/503/504 與連線層失敗）。
**替代方案**：各站自寫 try/except 迴圈。**不選的原因**：重試政策與站點無關、不該逐站客製；掛在共用 Session 零侵入、不動任何 `sites/*.py`。

## Risks / Trade-offs

- **型態 A 站明年可能另開新頁** → 頁面變空/抓不到當年度須知時「即告警」，人工補救；不靜默失敗。
- **Cloudflare/SPA 站不穩、且需開真瀏覽器** → 以 render（Playwright headless）或反偵測 Selenium 處理；接受這幾站較慢、偶爾需重跑。
- **`deadline` ≠ 計畫年度** → 年度判定一律以公告發布日為準；驗證資料庫年份時改用「檔名/內文修訂日/計畫期程」三面向讀內文，不單靠 deadline。
- **本機 console cp950 / 中文檔名限制** → `sys.stdout` 包 utf-8、輸出檔 utf-8-sig、程式與資料檔名一律英文。
- **`subsidies` 表混入約 42% 舊年度資料**（本次年份驗證發現：84/200 筆為 111~114 年度舊文件） → 需人工核對/清理，非抓取管線的 bug；也是「先獨立存放、不直接併入」決策的佐證。
- **後端完全獨立造成邏輯重複**（同段程式在 skills 與 `common/` 各一份） → 以「可獨立排程」為優先，接受重複；改動時兩邊各自維護、不互相 import。
- **各站編碼需逐站試錯**（`.text` / `.content` / 明確 `.decode`） → 沒有可靠的自動判斷規則，維持逐站處理；僅把重複的 decode 收斂為小工具＋新站判斷檢查清單，不做「智慧自動判斷」以免影響已測站。
