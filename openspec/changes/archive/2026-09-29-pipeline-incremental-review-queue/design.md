## Context

- 管線入口 `subsidy_crawler/pipeline.py::run_pipeline()`：爬蟲 → 萃取 → 去重 → `db.sync_to_db(csv)`；`--skip-db` 跳過最後一步。
- `common/db.py::sync_to_db()` 目前流程：讀成功列 → `_backup()`（docker exec pg_dump）→ 交易內 TRUNCATE＋逐筆 INSERT → 驗證筆數才 COMMIT。`_load_success_rows()`、`_map_row()`、`_backup()`、`connect()` 都可以直接沿用。
- `subsidies` 的 schema 是手動建的（repo 裡沒有 init SQL；schema 見 `data/db_backup_20260822_124231.sql`）：`id` serial PK、`title` varchar(255)、`category` varchar(50)、`amount` varchar(50)、`start_date` varchar(50)、其餘 text、`created_at` 預設 now。**沒有任何 UNIQUE 限制**。
- `postprocess.py` 已有 `_sim(a, b)`（正規化後的 SequenceMatcher ratio）和 `TITLE_SIM_TH = 0.85`。
- `run_pipeline.bat` 已經會把輸出附加到 `data/pipeline_run.log`，並記錄 exit code。
- 實測依據（8/26 168 筆 vs 8/31 160 筆）：用（機關, 連結）判定為新案的 5 筆中，有 3 筆其實是換了網址的舊案，標題相似度 0.98–1.00。同一個連結重新萃取時，描述有 132/155 筆文字不同，所以已知案不更新內容。

## Goals / Non-Goals

**Goals:**
- 改寫 `db.py` 的同步邏輯，改成跟 specs 一致的增量比對＋待審佇列，不影響前端現有讀 `subsidies` 的路徑。
- 驗證能在另一個資料庫上完整跑一遍，正式資料完全不會被動到。

**Non-Goals:**
- 審核介面（Change B）。本 change 只提供 `approve_pending()` 和 `reject_pending()` 兩個函式。
- 已知案的內容更新、下架偵測、個別站點抓到 0 筆的告警。
- 寄信或 webhook 通知。
- 建立 Windows 排程任務本身（時間由使用者決定）。

## Decisions

### D1：待審表由程式以 `CREATE TABLE IF NOT EXISTS` 建立
- 做法：`db.ensure_pending_table(conn)` 在同步開始時呼叫，欄位沿用 `subsidies` 的型別，另加以下欄位和限制：
  - `status varchar(10) NOT NULL DEFAULT 'pending'`，加上 CHECK 限制只能是 pending／approved／rejected
  - `first_seen_at timestamp NOT NULL`
  - `reviewed_at timestamp NULL`
  - `suspected_dup_of integer NULL`
  - `UNIQUE(category, source_url)`
- 為什麼：repo 沒有 migration 工具，`subsidies` 也是手動建的。用冪等的建表語句，第一次執行時自己把表建起來，不需要另外手動操作。
- 考慮過但不採用：另外寫一份 init SQL 讓使用者手動跑，多一個步驟，容易忘記。

### D2：比對在 Python 端做，不用 SQL JOIN
- 做法：交易開始後，把 `subsidies` 的 `(id, category, source_url, title)` 和 `subsidies_pending` 的 `(category, source_url)` 全部讀出來，建成 set／dict，在記憶體裡判斷。
- 為什麼：資料量只有幾百筆，全部讀出來很快。標題相似度要用 `postprocess._sim()`，本來就只能在 Python 裡算。
- 比對 key：`(category.strip(), source_url.strip())`，也就是 `_map_row()` 的輸出。比對時不額外轉大小寫或解碼 URL，跟 UNIQUE 限制用同一個定義。
- 同一批資料裡如果出現相同的 key：取第一筆，後面的算成跳過。postprocess 之後理論上不會發生，這裡只是防呆。

### D3：疑似舊案只跟 `subsidies` 裡同機關、同網域的案子比
- 做法：同機關且連結網域相同（小寫、去 www.）的每個既有案都算一次 `_sim(新標題, 舊標題)`，取最高分。≥ `TITLE_SIM_TH` 就把 `suspected_dup_of` 設成那筆舊案的 `subsidies.id`。
- 為什麼：spec 要求記下舊案 id，正式表才有穩定的 id 可以指。待審表裡還沒審的案子不拿來比，避免待審案互相指來指去。
- 為什麼要同網域（驗證時發現）：各縣市地方型 SBIR 的申請機關都對映成中小企業署，標題只差縣市名（相似度 ≥ 0.85），只看機關會把金門標成苗栗、臺中標成臺南的舊案。實測網址換掉的舊案（industry-incentive.taipei、aoc.gov.tw、eii.nat.gov.tw）都是同網域內換路徑。代價：機關整站搬網域時不會有提示，但案子仍進待審。
- 重用方式：直接 `from ..postprocess import _sim, TITLE_SIM_TH`，不另外寫一份相似度函式。要確認 postprocess 在模組層級沒有副作用。

### D4：同步函式改名成 `sync_new_to_pending()`，回傳統計數字
- 做法：回傳 `{"success_rows", "new", "skipped_known", "suspected_dup", "new_rows"}`，供摘要使用。舊的 `sync_to_db` 直接移除，不保留相容名稱，因為只有 pipeline.py 在呼叫它。
- 原本的「0 筆成功列拒絕」保護照舊保留：成功列是 0 筆通常代表管線出了問題，直接拋例外，後面會觸發告警。
- 驗證方式：INSERT 用 `RETURNING id` 收集本次 id，寫入後查 `SELECT count(*) ... WHERE id = ANY(本次 id)`，確認筆數等於新案數，不一致就 rollback。（原本用 `first_seen_at = run_at` 計數，驗證時發現同一秒內跑兩次會算到別次的列，已改。）
- 備份：只有本次有新案才執行 `_backup()`。沒有新案時完全不寫資料庫，也就不需要備份，可以避免 `db_backup_*.sql` 每週無意義地累積。

### D5：審核操作 `approve_pending(ids)` 和 `reject_pending(ids)`
- 做法：兩者都在單一交易裡執行 `SELECT ... FOR UPDATE WHERE id = ANY(%s) AND status = 'pending'`，找到的筆數跟傳入的 id 數量不一致就拋例外。
  - approve：先 `_backup()`，再把該筆的內容欄位 INSERT 進 `subsidies`，最後 UPDATE status 和 reviewed_at。
  - reject：只 UPDATE status 和 reviewed_at，不需要備份。
- 為什麼：Change B 的審核頁只要透過 dev_api 呼叫這兩個函式就好，交易和驗證的邏輯集中在 db.py 一個地方。

### D6：摘要和告警放在新模組 `common/monitor.py`，由 `pipeline.py` 外層包起來
- 做法：`run_pipeline()` 每個階段更新一個 `summary` dict，整段包在 try/except/finally 裡：
  - `finally`：寫 `run_summary.json`
  - `except`：追加一筆「管線失敗」告警到 `alerts.log`，然後重新拋出例外，讓 exit code ≠ 0
  - 萃取失敗比例：從去重後的最終 CSV 算。分母＝全部列，分子＝`萃取模型` 空白的列（跟 `postprocess.py` 判斷失敗的方式一樣）。去重後結果是 0 列時不算比例。
  - 爬到的筆數：`1_crawled_raw.jsonl` 的行數
- 為什麼：不必改爬蟲和萃取模組的內部，所有數字都從各階段已經產出的檔案讀。`alerts.log` 用純文字，一行一筆（時間 \t 類型 \t 說明），Excel 或記事本都能直接打開。
- `--skip-db` 時：摘要裡資料庫相關的欄位為空，但一樣寫摘要、一樣判斷告警。

### D7：資料庫名稱可以用環境變數覆蓋
- 做法：`connect()` 和 `_backup()` 改成：如果 `os.environ` 有 `POSTGRES_DB` 就用它，沒有才讀 `.env`。
- 為什麼：驗證時用 `POSTGRES_DB=palantir_verify`，在另一個測試資料庫上跑，正式的 `palentir_test_db` 完全不會被碰到。目前 `POSTGRES_HOST`、`POSTGRES_PORT` 已經是讀環境變數，這裡照同樣的做法。

### D8：排程入口沿用 `run_pipeline.bat`
- 做法：保留現在的寫法，只在最後加上 `exit /b %errorlevel%`，讓工作排程器看得到失敗。
- 在 `subsidy_crawler/README.md` 補一節 Windows 工作排程器的設定步驟：觸發條件、啟動位置、以系統管理員身分執行、「如果錯過排程則盡快執行」。
- 時間先不寫死，由使用者測完再決定。

## Risks / Trade-offs

- [網址換了的舊案變成待審] → 用 `suspected_dup_of` 標出來，在審核時處理；不會自動跳過，避免漏掉同名的新年度計畫。
- [機關真的在同一個網址上改了內容（例如截止日延長）] → 目前抓不到，這是接受的代價（proposal 已說明）。實務上大多會換新檔、網址也會變，這種情況會以新案的身分出現。
- [`subsidies` 沒有 UNIQUE 限制，審核核准時有可能重複插入] → `approve_pending` 只接受 pending 狀態的記錄，同一筆不會被核准兩次，加上比對 key 本身已經避開重複。之後要不要在 `subsidies` 加 UNIQUE，留給 Change B 決定。
- [`category` 是 varchar(50)，機關名稱太長會寫入失敗] → 待審表沿用同樣的型別。寫入失敗會觸發 rollback 和告警，不會留下一半的資料。現有對映表的機關名稱都 < 50 字。
- [電腦沒開，排程沒有執行，也不會產生任何告警] → 已知限制。Change B 的審核頁會顯示 `run_summary.json` 的結束時間，讓人看得出上次是什麼時候跑的。
- [從 postprocess 匯入私有函式 `_sim`] → 兩個模組是同一個套件，影響可控；在 design 記下這個相依，之後如果要改相似度函式，要記得兩邊一起看。

## Migration Plan

1. 實作前先 archive `pipeline-chaining` 和 `pipeline-db-sync`，讓 `subsidy-db-sync` 的主 spec 存在，這個 change 的 MODIFIED／REMOVED 才能套用。
2. 部署：合併程式之後，第一次執行管線就會自動建立 `subsidies_pending`。這時 `subsidies` 裡的 165 筆就是比對起點（8/31 那次 160 筆結果中有 6 筆不在正式表，第一次正式執行會進待審），不需要額外搬資料。
3. 回滾：把程式 revert 回舊版，再 `DROP TABLE subsidies_pending` 即可；`subsidies` 從頭到尾都沒被動過。

## Open Questions

- `run_summary.json` 要不要另外保留歷史紀錄（例如 `data/run_history/`）？目前只保留最新一次，`alerts.log` 會累積。之後有需要再加，不影響 spec。
