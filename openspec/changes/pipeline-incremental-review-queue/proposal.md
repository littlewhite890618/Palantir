## Why

路線圖 N1「新案上線通知」（9/16–9/30）要先知道「這次比上次多了哪些補助案」，但目前 `common/db.py` 每次都是整表 TRUNCATE＋全量 INSERT，資料庫分不出新舊；而且管線要改成排程、無人看管地執行，跑完成功與否也沒有任何紀錄可以查。這個 change 把資料庫同步改成「增量偵測＋待審佇列」，並加上執行摘要與告警，讓後續的審核頁與前端通知（Change B）有資料來源。

## What Changes

- **BREAKING** 管線不再寫入正式表 `subsidies`：移除整表 TRUNCATE＋INSERT 的同步路徑，現有 `subsidies` 的內容原樣保留，作為增量比對的起點。
- 新增待審表 `subsidies_pending`：欄位＝`subsidies` 的欄位，再加上 `status`（pending／approved／rejected）、`first_seen_at`、`reviewed_at`、`suspected_dup_of`。管線只會把「新案」寫進這張表。
- 增量偵測分兩層：
  1. 用（申請機關, 連結）比對 `subsidies`＋`subsidies_pending`，比對到就視為已知案，直接跳過。已知案不更新內容，rejected 的案子也不會再進待審。
  2. 比對不到的案子，再跟同機關的既有案子比標題相似度。相似度 ≥ 0.85 的一樣寫進待審，但標記「疑似舊案」，並記下對應的舊案 id。
- 這次沒抓到的舊案不處理（不刪除、不標記）。
- 新增「審核通過寫入正式表」的函式，供 Change B 的審核頁呼叫；本 change 不做審核介面。
- 「本次新增」報表：待審表的 `first_seen_at` 記錄本次執行時間，另外輸出 `data/new_this_run.csv`（每次覆蓋）。
- 執行摘要與告警（只寫檔，不寄信、不接 n8n）：
  - 每次執行都寫 `data/run_summary.json`。
  - 以下兩種情況會追加一筆到 `data/alerts.log`：管線例外或 exit code≠0；萃取失敗比例 ≥ 10%。
- 排程：沿用 `run_pipeline.bat`＋Windows 工作排程器，只補設定步驟說明。執行時間由使用者測試後再決定，本 change 不建立排程任務。
- 資料庫名稱可用環境變數覆蓋，讓驗證可以在測試資料庫上跑，不動正式資料。

## Capabilities

### New Capabilities
- `subsidy-review-queue`：增量偵測（兩層比對）、待審表 `subsidies_pending` 的內容與狀態、本次新增報表、審核通過寫入正式表的契約。
- `pipeline-run-monitoring`：每次執行的摘要檔、告警條件與告警檔、Windows 排程的執行入口。

### Modified Capabilities
- `subsidy-db-sync`：原本「管線結果整批同步進 subsidies 表（整表覆蓋）」的需求改成「管線不直接寫 subsidies、改寫待審表」。備份、交易安全、只寫成功列、欄位對應、跳過旗標沿用，套用對象從 `subsidies` 改成 `subsidies_pending`。（這項能力定義在尚未 archive 的 `pipeline-db-sync` change；本 change 實作前要先 archive 它，main spec 才會存在。）

## Impact

- **修改**：`subsidy_crawler/common/db.py`（同步邏輯改寫、建表、兩層比對、審核通過寫入函式、資料庫名稱可覆蓋）、`subsidy_crawler/pipeline.py`（階段 4 改呼叫增量同步，外層加摘要與告警）。
- **沿用不改**：`postprocess.py` 的相似度函式 `_sim()` 與門檻 `TITLE_SIM_TH`（匯入重用）、爬蟲、萃取、去重邏輯、`run_pipeline.bat`。
- **資料庫**：新增 `subsidies_pending` 表；`subsidies` 的 schema 與內容不變。
- **下游**：`export_subsidies`、`dev_api.py` 仍讀 `subsidies`，行為不變。之後新案要等審核通過才會出現在前端。
- **文件**：Windows 工作排程器設定步驟（寫進 `subsidy_crawler/README.md`）。
- **依賴**：無新增外部套件。
