## 1. 依賴與連線基礎

- [x] 1.1 `subsidy_crawler/requirements.txt` 補上 `psycopg2`
- [x] 1.2 `subsidy_crawler/common/db.py`：寫 `.env` parser（沿用 `export_subsidies.py` 手法，不用 python-dotenv）與 `_connect()`（host/port 預設 `localhost`/`5434`，dbname/user/password 從 `.env` 讀）
- [x] 1.3 `subsidy_crawler/.gitignore` 補 `data/db_backup_*.sql`（比照既有 `data/*.csv`／`data/*.jsonl` 排除慣例）

## 2. 讀取與欄位對應

- [x] 2.1 `db.py`：讀輸入 CSV，篩出「萃取模型」欄位非空的成功列（沿用 `extract_fields.py::load_done()` 同款判斷式）
- [x] 2.2 `db.py`：實作欄位對應函式（15欄→12欄），依 spec 的對應表：`標題→title`、`申請機關→category`、`補助金額上限(空則補助比例)→amount`、`申請截止日期→deadline`、`描述→description`、`連結→source_url`、`申請資格→eligibility`、`應備資料→required_documents`、`申請方式→application_method`、`諮詢窗口→contact_window`；`start_date`/`subsidy_timeline` 留空；不寫入部門/萃取模型/規則交叉檢查/備註
- [x] 2.3 空成功列（0筆）時直接中止並報錯，不執行後續清空/寫入

## 3. 備份

- [x] 3.1 `db.py`：`_backup()` 用 `subprocess` 呼叫 `docker exec postgres pg_dump -U admin palentir_test_db`，輸出到 `subsidy_crawler/data/db_backup_<時間戳>.sql`
- [x] 3.2 備份指令失敗（含 docker/container 未啟動）時直接中止，不繼續往下執行清空/寫入

## 4. 交易寫入與驗證

- [x] 4.1 `db.py::sync_to_db(csv_path)`：開交易 → `TRUNCATE subsidies` → 逐筆參數化 `INSERT`
- [x] 4.2 寫入完成後 `SELECT count(*)`，與預期成功列數不一致就 `rollback()` 並報錯；一致才 `commit()`
- [x] 4.3 任何步驟拋例外都要 `rollback()`，確保資料庫回到執行前狀態
- [x] 4.4 印出摘要（備份路徑、寫入筆數、耗時）

## 5. 與 pipeline.py 整合

- [x] 5.1 `pipeline.py::run_pipeline()` 新增 `skip_db=False` 參數，`postprocess.run()` 完成後、非 `skip_db` 時呼叫 `db.sync_to_db(最終CSV路徑)`
- [x] 5.2 CLI `main()` 新增 `--skip-db` 旗標，傳入 `run_pipeline()`

## 6. 驗證

- [x] 6.1 用少量假資料測試 `sync_to_db()`：正常路徑筆數正確；模擬中途拋例外能正確 rollback、資料庫回到執行前狀態（實測：故意寫超長標題觸發 `varchar(255)` 違反，確認 TRUNCATE 也一併被撤銷、回到執行前 2 筆的狀態）
- [x] 6.2 用手上已有的真實測試結果 CSV（非正式 `data/` 檔案）試跑一次完整寫入，人工核對資料庫內容筆數與欄位正確（161筆全部寫入成功；過程中發現 `deadline` 欄位 `varchar(50)` 不夠長，3筆多梯次截止日超長，已與使用者確認後執行 `ALTER TABLE subsidies ALTER COLUMN deadline TYPE text`，改完重跑成功）
- [x] 6.3 確認空成功列輸入會中止、不清空既有資料（實測：全部是失敗列的輸入正確拋錯，資料庫維持原狀、也沒有產生備份檔）
- [x] 6.4 確認 `--skip-db` 能正確跳過寫入、其餘管線行為（爬蟲/萃取/去重輸出檔案）不變（把三段管線函式換成空函式，驗證 `skip_db=True/False` 時 `db.sync_to_db()` 分別被呼叫 0 次/1 次）
- [x] 6.5 確認備份檔案正確產生於 `data/`、且被 `.gitignore` 排除（每次成功進入清空階段前都產生一份 `db_backup_*.sql`，`git status` 確認未被追蹤）
- [x] 6.6 `openspec validate pipeline-db-sync --strict` 通過
