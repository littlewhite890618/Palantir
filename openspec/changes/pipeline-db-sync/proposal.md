## Why

`subsidy_crawler` 三段管線（爬蟲→萃取→去重，`pipeline-chaining` change 已完成）目前只輸出到本機 CSV/JSONL 檔案，沒有接到任何資料庫。專案裡既有一張 PostgreSQL `subsidies` 表（Docker `postgres` container、db `palentir_test_db`），是已上線的 Palantir 前端（`https://tianhwaservice.github.io/palantir/`）查詢補助案的資料來源；這張表原本由另一套 n8n 工作流程（廣泛網路搜尋+AI萃取）寫入，現已決定停用、改由 `subsidy_crawler` 成為唯一資料來源。目前該表是空的，需要把管線的結構化萃取結果實際寫進去，前端才有資料可查。

## What Changes

- 新增 `subsidy_crawler/common/db.py`：提供 `sync_to_db(csv_path)`，把萃取+去重後的最終結果寫入 `subsidies` 表。
- 這次為**簡化版**：每次執行皆為「整表 TRUNCATE + 全量 INSERT」，不做既有列比對/UPDATE、也不做「這次沒抓到的舊列」保留或刪除判斷——資料庫每次跑完就是這次管線輸出的完整快照。比對式增量同步（判斷「同一筆補助案」、內容變更時更新而非整表重建）留待下一輪 change。
- 只寫入「成功列」（`萃取模型` 欄位有值者），失敗列不進資料庫。
- `pipeline.py` 新增 `--skip-db` CLI 旗標：預設會在去重完成後寫入資料庫；加此旗標可跳過寫入（測試時不動正式DB）。
- 寫入前自動 `pg_dump` 備份、整段用交易（transaction）包住，失敗可 rollback，寫完先驗證筆數才 COMMIT。
- `requirements.txt` 補上 `psycopg2` 依賴（既有 `export_subsidies` skill 已在用，這次補進主套件依賴清單）。
- **不影響**既有 `export_subsidies`／`deploy_palantir` 兩個 skill 與 n8n 工作流程本身，這次只處理本機資料庫寫入，不觸發線上網站更新（仍需另外手動跑既有兩個 skill）。

## Capabilities

### New Capabilities

- `subsidy-db-sync`：把管線最終去重結果整批同步進 `subsidies` 資料表的能力，含欄位對應、只寫成功列、交易安全（備份+可rollback+驗證後才提交）、可選擇跳過寫入。

### Modified Capabilities

<!-- 無：既有 subsidy-pipeline-chaining 能力（爬蟲/萃取/去重/JSON交接）行為契約不變，本次只在其後新增一個消費最終輸出檔的新階段。 -->

## Impact

- **新增檔案**：`subsidy_crawler/common/db.py`。
- **修改檔案**：`subsidy_crawler/pipeline.py`（新增 `--skip-db` 旗標與呼叫 `db.sync_to_db()`）、`subsidy_crawler/requirements.txt`（補 `psycopg2`）、`subsidy_crawler/.gitignore`（排除 pg_dump 備份檔）。
- **外部系統**：本機 PostgreSQL `subsidies` 表（TRUNCATE+INSERT，寫入前自動備份）。不影響 GitHub Pages 上的線上網站（需另外手動匯出+部署）。
- **不影響**：三段管線本身（爬蟲/萃取/去重）邏輯與既有 CSV/JSONL 輸出格式不變；`export_subsidies`／`deploy_palantir` 兩個既有 skill 不變；n8n 既有工作流程不在本次變更範圍內。
