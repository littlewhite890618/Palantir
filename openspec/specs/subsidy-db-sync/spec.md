# subsidy-db-sync Specification

## Purpose
定義補助案管線最終去重結果同步進 PostgreSQL `subsidies` 資料表的行為契約：欄位對應、只寫成功列、交易安全（備份、可回滾、驗證後才提交），以及可選擇跳過寫入的行為，讓資料庫內容能安全地隨每次管線執行更新。
## Requirements
### Requirement: 只寫入成功列

系統 SHALL 只把「萃取模型」欄位有值（萃取成功）的列拿去做增量比對、寫入待審表 `subsidies_pending`；下載失敗、抽字失敗、LLM 萃取失敗等原樣保留的失敗列 MUST NOT 寫入任何資料表。

#### Scenario: 失敗列被排除

- **WHEN** 最終結果檔案中含有萃取模型欄位為空的失敗列
- **THEN** 該列不會出現在 `subsidies_pending` 的寫入結果中，其餘成功列不受影響

### Requirement: 欄位對應

系統 SHALL 依固定對應規則把管線輸出欄位轉換為資料表欄位（`subsidies_pending` 與 `subsidies` 共用同一套規則）：`標題→title`、`申請機關→category`、`補助金額上限→amount`（為空時退用補助比例）、`申請截止日期→deadline`、`描述→description`、`連結→source_url`、`申請資格→eligibility`、`應備資料→required_documents`、`申請方式→application_method`、`諮詢窗口→contact_window`；`start_date`、`subsidy_timeline` 兩欄位 SHALL 留空；`部門`（原始來源）、`萃取模型`、`規則交叉檢查`、`備註` 四欄 MUST NOT 寫入資料表。

#### Scenario: 申請機關對映到 category 而非原始部門

- **WHEN** 某列的「部門」為「金門縣」、「申請機關」為「經濟部中小及新創企業署」（SBIR 案例的 deterministic 對映結果）
- **THEN** 寫入的 `category` 值為「經濟部中小及新創企業署」，不是「金門縣」

#### Scenario: 金額上限為空時退用比例

- **WHEN** 某列「補助金額上限」為空、但「補助比例」有值
- **THEN** 寫入的 `amount` 欄位使用補助比例的值

### Requirement: 寫入前自動備份

系統 SHALL 在每次寫入資料庫（管線寫入待審表、或審核通過寫入正式表）之前，自動對資料庫執行備份並保存於本機；備份檔案 MUST NOT 進版控。

#### Scenario: 每次同步前產生備份

- **WHEN** 系統即將把本次新案寫入 `subsidies_pending`
- **THEN** 系統先產生一份本機資料庫備份檔案，備份成功後才繼續寫入；備份失敗則中止、不寫入

### Requirement: 交易安全與寫入驗證

系統 SHALL 把同一次同步的所有寫入包在同一個資料庫交易內；寫入完成後 SHALL 驗證實際新增筆數與預期一致，驗證通過才提交交易；任一步驟失敗時 SHALL 回滾，使資料庫維持在執行前的狀態，MUST NOT 留下只寫入一部分的中間狀態。

#### Scenario: 中途失敗完整回滾

- **WHEN** 交易中寫入到一半發生錯誤或中斷
- **THEN** 資料庫回滾至本次同步開始前的狀態，`subsidies` 與 `subsidies_pending` 都不會有部分寫入的資料

#### Scenario: 驗證筆數才提交

- **WHEN** 交易內所有新案寫入完成
- **THEN** 系統確認 `subsidies_pending` 實際新增的列數與本次判定的新案數一致後才提交；不一致則回滾並回報錯誤

### Requirement: 可選擇跳過資料庫寫入

管線的命令列介面 SHALL 提供旗標讓使用者跳過資料庫步驟；指定該旗標時，爬蟲、萃取、去重三階段 SHALL 正常執行並產出檔案結果，資料庫 MUST NOT 被觸碰（不比對、不寫入任何資料表）。

#### Scenario: 指定跳過旗標時不連線資料庫

- **WHEN** 使用者執行管線並指定跳過資料庫寫入的旗標
- **THEN** 系統完成爬蟲、萃取、去重並產出結果檔案，且不對 `subsidies` 或 `subsidies_pending` 做任何讀寫

