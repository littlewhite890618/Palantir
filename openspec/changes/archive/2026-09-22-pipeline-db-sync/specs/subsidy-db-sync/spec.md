## Purpose

定義補助案管線最終去重結果同步進 PostgreSQL `subsidies` 資料表的行為契約：欄位對應、只寫成功列、交易安全（備份、可回滾、驗證後才提交），以及可選擇跳過寫入的行為，讓資料庫內容能安全地隨每次管線執行更新。

## ADDED Requirements

### Requirement: 管線結果整批同步進 subsidies 表

系統 SHALL 在去重階段完成後，把最終結果的「成功列」整批寫入 `subsidies` 資料表；本版本 SHALL 採「整表覆蓋」語意：清空既有資料後寫入本次結果，不做逐筆比對或更新既有列。

#### Scenario: 一般執行流程寫入資料庫

- **WHEN** 管線完成爬蟲、萃取、去重，且未指定跳過寫入
- **THEN** 系統把去重後的成功列寫入 `subsidies` 表，寫入完成後表中內容即為本次執行的完整結果

#### Scenario: 空結果不清空既有資料

- **WHEN** 本次去重後的成功列數為 0
- **THEN** 系統 MUST NOT 清空 `subsidies` 表既有內容，SHALL 中止寫入並回報錯誤，避免因管線異常（如全部站點抓取失敗）而把資料庫清空

### Requirement: 只寫入成功列

系統 SHALL 只把「萃取模型」欄位有值（萃取成功）的列寫入 `subsidies` 表；下載失敗、抽字失敗、LLM 萃取失敗等原樣保留的失敗列 MUST NOT 寫入。

#### Scenario: 失敗列被排除

- **WHEN** 最終結果檔案中含有萃取模型欄位為空的失敗列
- **THEN** 該列不會出現在 `subsidies` 表的寫入結果中，其餘成功列不受影響

### Requirement: 欄位對應

系統 SHALL 依固定對應規則把管線輸出欄位轉換為 `subsidies` 表欄位：`標題→title`、`申請機關→category`、`補助金額上限→amount`（為空時退用補助比例）、`申請截止日期→deadline`、`描述→description`、`連結→source_url`、`申請資格→eligibility`、`應備資料→required_documents`、`申請方式→application_method`、`諮詢窗口→contact_window`；`start_date`、`subsidy_timeline` 兩欄位 SHALL 留空；`部門`（原始來源）、`萃取模型`、`規則交叉檢查`、`備註` 四欄 MUST NOT 寫入 `subsidies` 表。

#### Scenario: 申請機關對映到 category 而非原始部門

- **WHEN** 某列的「部門」為「金門縣」、「申請機關」為「經濟部中小及新創企業署」（SBIR 案例的 deterministic 對映結果）
- **THEN** 寫入 `subsidies` 表的 `category` 值為「經濟部中小及新創企業署」，不是「金門縣」

#### Scenario: 金額上限為空時退用比例

- **WHEN** 某列「補助金額上限」為空、但「補助比例」有值
- **THEN** 寫入的 `amount` 欄位使用補助比例的值

### Requirement: 寫入前自動備份

系統 SHALL 在清空 `subsidies` 表之前，自動對資料庫執行備份並保存於本機；備份檔案 MUST NOT 進版控。

#### Scenario: 每次同步前產生備份

- **WHEN** 系統即將執行整表覆蓋寫入
- **THEN** 系統先產生一份本機資料庫備份檔案，備份成功後才繼續清空與寫入

### Requirement: 交易安全與寫入驗證

系統 SHALL 把「清空既有資料」與「寫入本次結果」包在同一個資料庫交易內；寫入完成後 SHALL 先驗證筆數與資料庫實際回報的列數一致，驗證通過才提交交易；任一步驟失敗時 SHALL 回滾，使資料庫維持在執行前的狀態，MUST NOT 留下清空後未完整寫入的中間狀態。

#### Scenario: 中途失敗完整回滾

- **WHEN** 交易中寫入到一半（例如第 80 筆）發生錯誤或中斷
- **THEN** 資料庫回滾至本次同步開始前的狀態，既有資料不會遺失，也不會停留在「已清空但未寫滿」的狀態

#### Scenario: 驗證筆數才提交

- **WHEN** 交易內所有列寫入完成
- **THEN** 系統查詢資料庫目前列數，確認與本次應寫入的成功列數一致後才提交；不一致則回滾並回報錯誤

### Requirement: 可選擇跳過資料庫寫入

管線的命令列介面 SHALL 提供旗標讓使用者跳過資料庫寫入步驟；指定該旗標時，爬蟲、萃取、去重三階段 SHALL 正常執行並產出檔案結果，資料庫 MUST NOT 被觸碰。

#### Scenario: 指定跳過旗標時不連線資料庫

- **WHEN** 使用者執行管線並指定跳過資料庫寫入的旗標
- **THEN** 系統完成爬蟲、萃取、去重並產出結果檔案，且不對 `subsidies` 表做任何清空或寫入操作
