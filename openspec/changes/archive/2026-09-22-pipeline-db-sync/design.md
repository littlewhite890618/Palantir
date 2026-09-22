## Context

見 proposal.md（Why）。相關既有事實：

- `subsidies` 表現有 schema（已用 `docker exec postgres psql -U admin -d palentir_test_db -c "\d subsidies"` 實際查證）：`id, title, category, amount, start_date, deadline, description, created_at, source_url, subsidy_timeline, eligibility, required_documents, application_method, contact_window`，目前 0 筆。
  **2026-08-21 驗證階段修正**：`deadline` 原為 `varchar(50)`，實測真實 161 筆資料時，3 筆「多梯次全部列出」的截止日超過 50 字（最長 77 字，屬萃取引擎既有的刻意設計，非資料異常）導致寫入失敗。與使用者確認後執行 `ALTER TABLE subsidies ALTER COLUMN deadline TYPE text`，改成跟 `description`/`eligibility` 等既有長文字欄位一致的 `text`（無上限），避免未來梯次更多時再次撞到長度限制。`title`/`category`/`amount`/`start_date` 目前維持原長度（`category`/`amount` 實測 161 筆皆無超過 50 字）。
- `.claude/skills/export_subsidies/scripts/export_subsidies.py` 已有一套驗證過可用的連線模式：手寫 `.env` parser（不用 python-dotenv）、`psycopg2.connect(host=..., port=..., dbname=..., user=..., password=...)`，host/port 預設 `localhost`/`5434`，其餘從 `.env` 讀。本次 `db.py` 沿用同一套模式，不重新設計。
- `md/DEPLOY_FRONTEND.md` 已記載的既有慣例：「改資料的安全流程：先 pg_dump 備份 → 用 BEGIN…COMMIT 交易包住 → 先 SELECT 預覽確認無誤才 COMMIT」，備份指令 `docker exec postgres pg_dump -U admin palentir_test_db`。
- `subsidy_crawler` 三段管線的既有輸出契約（`pipeline-chaining` change）：`postprocess.run(in_path, out_csv, ...)` 執行完會把最終去重結果覆蓋寫到 `out_csv`（及同路徑 `.jsonl`）。`pipeline.py::run_pipeline()` 目前依序呼叫 `run.run_all()` → `extract_fields.run()` → `postprocess.run()`，回傳最終 CSV 路徑。

## Goals / Non-Goals

**Goals:**
- 讓管線最終結果能安全地整批進到 `subsidies` 表，供既有 `export_subsidies`／`deploy_palantir` 流程後續使用。
- 寫入失敗或中斷時，資料庫不會停在壞掉的中間狀態。
- 提供跳過寫入的方式，方便開發/測試不動到正式資料庫。

**Non-Goals:**
- 不做「同一筆補助案」的比對/更新邏輯（標題正規化、內容相似度加權評分等）——這是下一輪 change 的範圍，這次是有意的簡化（整表覆蓋）。
- 不處理「這次沒抓到但資料庫裡有」的列要不要保留/刪除/標記過期——本版本每次都是整表重建，此問題不存在於本次語意下。
- 不觸發或修改 `export_subsidies`／`deploy_palantir`，資料寫進本機 DB 後，線上網站更新仍是既有的手動兩步驟。
- 不修改 n8n 既有工作流程本身（使用者已決定停用該資料來源，但改動 n8n 端不在本次程式碼變更範圍）。

## Decisions

- **整表 TRUNCATE + 全量 INSERT，而非逐筆比對 UPDATE/INSERT**：使用者已明確定案「這次先不做比對邏輯」。理由：判斷「同一筆補助案」需要處理標題不穩定（同一文件不同次 LLM 萃取標題會飄）、網址會變（政府網站附件連結常換）、罐頭法條文字灌高相似度等已在對話中用真實資料驗證過的風險，屬於需要獨立設計與校準（類似規則5的0.75/0.85門檻校準過程）的課題，不適合跟「先把資料寫進DB」這個更基礎的需求綁在一起。整表覆蓋是最小可行版本，之後升級為比對式同步時，只需替換 `db.py` 內部實作，外部呼叫介面 `sync_to_db(csv_path)` 不變。
- **空結果拒絕寫入（不清空既有資料）**：這是本次新增的安全閘門，原設計沒有明講但實作時必須處理——如果管線異常（例如爬蟲階段整批失敗、或呼叫時誤傳空檔案），整表覆蓋語意會導致「用 0 筆清空掉資料庫」這種比不寫入更糟的結果。所以 `sync_to_db` 讀到 0 筆成功列時 SHALL 直接中止並報錯，不執行 TRUNCATE。
- **寫入前自動 pg_dump 備份**：沿用 `DEPLOY_FRONTEND.md` 既有的人工慣例，改成程式自動做。實作用 `subprocess` 呼叫 `docker exec postgres pg_dump -U admin palentir_test_db`（與文件記載指令一致），輸出導到本機檔案（例如 `subsidy_crawler/data/db_backup_<時間戳>.sql`）。選用 `subprocess` 呼叫既有 docker 指令而非改用 psycopg2 自己組 dump 邏輯，因為 `pg_dump` 本身就是最穩妥、專案已驗證可行的備份方式，沒有理由用程式重造。
- **交易 + 驗證筆數才 COMMIT**：`BEGIN` → `TRUNCATE subsidies` → 逐筆 `INSERT`（參數化查詢） → `SELECT count(*)` 核對筆數與預期一致 → `COMMIT`；任何步驟拋例外就整段交易 rollback（`psycopg2` 連線預設不自動 commit，顯式呼叫 `conn.rollback()`/`conn.commit()` 即可，不需要手寫 SAVEPOINT）。
- **只寫成功列的判斷依據**：沿用 `extract_fields.py::load_done()` 已經在用的同一個判斷式——「萃取模型」欄位（`(row.get("萃取模型") or "").strip()`）非空即成功，不新增判斷邏輯。
- **`--skip-db` 預設關閉（即預設會寫入資料庫）**：使用者已在先前討論定案「pipeline.py 新增第4階段，自動連發」，這次沿用同一個決定，跳過寫入需要主動加旗標，對稱於既有 `--keep-cache`（預設清除、要主動保留）的旗標風格。
- **`psycopg2` 補進 `requirements.txt`**：`subsidy_crawler` 目前的依賴清單沒有這個套件，但 `export_subsidies.py` 已經在用、環境已安裝，純粹補齊清單完整性，不是新風險。

## Risks / Trade-offs

- [整表覆蓋語意下，`id` 每次都會變動（TRUNCATE 後從頭編號）] → 目前沒有其他系統依賴固定 `id`（`export_subsidies.py` 只是 `SELECT * ORDER BY id` 匯出，不依賴特定id值），可接受；若之後有系統開始依賴固定 id，需在比對式同步（下一輪）中一併處理。
- [下一輪要換成比對式同步時，TRUNCATE 語意與「保留 id、只 UPDATE 變更列」互斥，屆時需要重寫大半 `db.py` 邏輯，而非漸進擴充] → 已在 proposal 中明講這是刻意的簡化版、預期會被取代，外部呼叫介面（`sync_to_db(csv_path)`）保持穩定，重寫範圍侷限在函式內部實作。
- [自動 pg_dump 依賴本機 Docker 環境已啟動（`postgres` container 執行中）] → 若 container 未啟動，`subprocess` 呼叫會失敗，`sync_to_db` 應該在備份失敗時直接中止、不繼續往下清空資料表（備份是清空前的必要前提，備份失敗等於沒有安全網）。
- [欄位對應把「部門」捨棄、只留「申請機關」] → 若日後前端想同時顯示「原始地方機關」與「中央對映機關」兩種資訊，目前設計會遺失原始「部門」值；已在 proposal 的 Impact 註明只寫入已定案的欄位對應，若日後有此需求需另外評估是否加欄位。

## Migration Plan

純新增行為，無資料遷移（目標表目前是空的）。回滾＝移除 `db.py`、`pipeline.py` 內對它的呼叫與 `--skip-db` 旗標；資料庫端可用寫入前產生的 pg_dump 備份還原。建議上線順序：先用少量假資料驗證 `sync_to_db()` 本身的交易/回滾行為，再用一次手上已有的真實測試結果試跑，人工核對資料庫內容後，才讓 `pipeline.py` 預設把這階段接上。
