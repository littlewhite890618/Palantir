## 1. 前置

- [x] 1.1 archive `pipeline-chaining` 與 `pipeline-db-sync`（`openspec archive`），確認 `openspec/specs/subsidy-db-sync/spec.md` 已產生
- [x] 1.2 `openspec validate pipeline-incremental-review-queue` 通過（MODIFIED/REMOVED 對得上主 spec）

## 2. 連線與建表（common/db.py）

- [x] 2.1 `connect()`、`_backup()`：`POSTGRES_DB` 優先讀環境變數，沒有才讀 `.env`（D7）
- [x] 2.2 `ensure_pending_table(conn)`：`CREATE TABLE IF NOT EXISTS subsidies_pending`，欄位沿用 subsidies 型別＋`status`(CHECK)／`first_seen_at`／`reviewed_at`／`suspected_dup_of`＋`UNIQUE(category, source_url)`（D1）

## 3. 增量同步（common/db.py）

- [x] 3.1 `sync_new_to_pending(csv_path, run_at)`：讀成功列（沿用 `_load_success_rows`／`_map_row`），0 筆成功列拋例外
- [x] 3.2 讀 subsidies `(id, category, source_url, title)` 與 pending `(category, source_url)`，依 key 判定已知案／新案；批內重複 key 取第一筆（D2）
- [x] 3.3 新案做疑似舊案判定：同機關 subsidies 標題取最高 `_sim()`，≥ `TITLE_SIM_TH` 設 `suspected_dup_of`（從 `postprocess` 匯入，D3）
- [x] 3.4 有新案才 `_backup()`；交易內 INSERT pending（status=pending、first_seen_at=run_at），驗證本次 INSERT 回傳的 id 筆數等於新案數才 COMMIT（原用 first_seen_at 計數，同秒重跑會誤判，已改），否則 rollback（D4）
- [x] 3.5 輸出 `data/new_this_run.csv`（標題、申請機關、連結、疑似舊案、對應舊案 id），沒有新案也寫表頭
- [x] 3.6 回傳統計 dict（success_rows／new／skipped_known／suspected_dup／new_rows）；移除舊的 `sync_to_db` 與 TRUNCATE 路徑，更新模組 docstring

## 4. 審核操作（common/db.py，供 Change B 使用）

- [x] 4.1 `approve_pending(ids)`：單一交易 `FOR UPDATE` 鎖 pending 列、筆數不符就拋例外、`_backup()` 後 INSERT 進 subsidies、UPDATE status=approved＋reviewed_at（D5）
- [x] 4.2 `reject_pending(ids)`：同樣只接受 pending，UPDATE status=rejected＋reviewed_at

## 5. 摘要與告警（common/monitor.py＋pipeline.py）

- [x] 5.1 新增 `common/monitor.py`：`write_summary(summary)`（覆蓋 `data/run_summary.json`）、`append_alert(kind, msg)`（追加 `data/alerts.log`，一行一筆 時間\t類型\t說明）
- [x] 5.2 `pipeline.py::run_pipeline()`：各階段更新 summary（爬到筆數＝crawled jsonl 行數、萃取成功/失敗＝最終 CSV 的 `萃取模型` 空白判斷、DB 統計），階段 4 改呼叫 `sync_new_to_pending`
- [x] 5.3 外層 try/except/finally：finally 寫摘要；except 記失敗階段＋錯誤訊息、寫「管線失敗」告警後重新拋出
- [x] 5.4 萃取失敗比例 ≥ 10% 寫「萃取失敗比例過高」告警（總列數 0 時不算）；`--skip-db` 時 DB 欄位留空但照常寫摘要與判斷告警
- [x] 5.5 `run_pipeline.bat` 結尾加 `exit /b %errorlevel%`（D8）

## 6. 文件

- [x] 6.1 `subsidy_crawler/README.md` 補「Windows 工作排程器設定」一節（觸發、啟動位置、錯過排程盡快執行），時間留給使用者決定（原寫 DEV_WORKFLOW.md，但那份是規格流程文件，改放操作說明所在的 README）
- [x] 6.2 `md/PALANTIR_SPEC.md`／`md/PROGRESS.md` 更新：subsidies 不再整表覆蓋、新增 subsidies_pending、排程＋監控子任務進度

## 7. 驗證（測試資料庫 `palantir_verify`，不跑爬蟲、不動正式資料）⚠️ 等使用者說可以再執行

- [x] 7.1 建測試資料庫，從正式庫當場 pg_dump 複製 subsidies（165 筆；不用舊的 db_backup_20260822，那份是 8/22 寫入前的舊資料）
- [x] 7.2 `POSTGRES_DB=palantir_verify` 對現有 `3_extracted_final.csv`（160 成功列）跑同步 → 新增 6 筆、跳過 154 筆、`new_this_run.csv` 6 列；再跑一次 → 新增 0 筆、報表只有表頭
- [x] 7.3 測試庫 subsidies 刪 3 筆（CSV 裡有的）再跑 → pending 新增 3 筆、報表 3 列
- [x] 7.4 把其中 1 筆 reject、改 1 筆標題相似舊案的連結 → 驗證 rejected 不再進待審、`suspected_dup_of` 有值
- [x] 7.5 `approve_pending`／`reject_pending` 各跑一次，含重複核准被拒
- [x] 7.6 餵失敗比例 ≥10% 的假 CSV、讓 DB 連線失敗 → `alerts.log` 各有一筆、`run_summary.json` 正確、exit code≠0
- [x] 7.7 確認正式 `palentir_test_db.subsidies` 仍是 165 筆、正式庫沒有 subsidies_pending；刪除測試資料庫
