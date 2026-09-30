# subsidy-review-queue Specification

## Purpose
定義管線如何從每次抓取結果中辨識「新補助案」、把新案放進待審表等候人工審核，以及審核通過後寫入正式表的行為契約，作為 N1 新案上線通知的資料來源。
## Requirements
### Requirement: 管線不直接寫入正式表

管線執行時 MUST NOT 新增、修改或刪除正式表 `subsidies` 的任何列；正式表只能透過「審核通過寫入」的操作改變。

#### Scenario: 一般執行後正式表不變

- **WHEN** 管線完成一次完整執行（含資料庫步驟）
- **THEN** `subsidies` 的列數與每一列內容都跟執行前完全相同

### Requirement: 以申請機關加連結辨識已知案

系統 SHALL 以（申請機關, 連結）作為補助案的身分；本次成功列的身分若已存在於 `subsidies`，或已存在於 `subsidies_pending`（不論狀態是 pending、approved 或 rejected），SHALL 視為已知案並跳過，MUST NOT 更新既有列的任何內容。

#### Scenario: 已在正式表的案子被跳過

- **WHEN** 本次抓到的某案，其（申請機關, 連結）跟 `subsidies` 的某一列相同，但描述文字不同
- **THEN** 該案不寫入 `subsidies_pending`，`subsidies` 那一列的描述維持原樣

#### Scenario: 已退回的案子不再進待審

- **WHEN** 本次抓到的某案，其身分跟 `subsidies_pending` 裡一筆 status＝rejected 的列相同
- **THEN** 該案不會再新增一筆待審，既有那筆的狀態維持 rejected

#### Scenario: 待審中的案子不重複新增

- **WHEN** 連續兩次執行都抓到同一個尚未審核的新案
- **THEN** `subsidies_pending` 中該案只有一筆，`first_seen_at` 維持第一次被抓到的時間

### Requirement: 新案寫入待審表

身分不屬於已知案的成功列 SHALL 寫入 `subsidies_pending`，狀態為 pending，`first_seen_at` 記錄本次執行時間，`reviewed_at` 為空。`subsidies_pending` MUST 包含 `subsidies` 的所有內容欄位，並以（申請機關, 連結）為唯一。

#### Scenario: 新案出現在待審表

- **WHEN** 本次抓到一個（申請機關, 連結）從未出現過的案子
- **THEN** `subsidies_pending` 新增一筆該案，status＝pending、first_seen_at＝本次執行時間

#### Scenario: 第一次啟用時不把既有資料當成新案

- **WHEN** 待審表剛建立，用內容跟現有 `subsidies` 完全相同（身分 key 全部一致）的結果執行同步
- **THEN** `subsidies_pending` 新增 0 筆

### Requirement: 疑似舊案標記

新案寫入待審表時，系統 SHALL 跟 `subsidies` 裡申請機關相同、且連結網域相同（忽略大小寫與開頭的 www.）的案子比對標題相似度；最高相似度 ≥ 0.85 時，SHALL 在該筆待審記錄註記對應舊案的 id（`suspected_dup_of`），但仍然以 pending 寫入待審，MUST NOT 自動跳過。沒有相似舊案時 `suspected_dup_of` 為空。

#### Scenario: 換了網址的舊案被標記

- **WHEN** 某案標題跟 `subsidies` 裡同機關的 id＝42「產業發展創業補助」完全相同，但連結不同
- **THEN** 該案寫入 `subsidies_pending`，status＝pending，`suspected_dup_of`＝42

#### Scenario: 不同網域的相似標題不互相標記

- **WHEN** 新案「金門縣地方產業創新研發推動計畫」（kinmensbir.org.tw）跟 `subsidies` 裡同機關的「地方產業創新研發推動計畫」（miaoli.gov.tw）標題相似度 ≥ 0.85
- **THEN** 因為網域不同，`suspected_dup_of` 為空

#### Scenario: 不同機關的同名案不互相標記

- **WHEN** 某案標題跟另一個機關的既有案相同
- **THEN** `suspected_dup_of` 為空

### Requirement: 本次新增報表

每次執行資料庫步驟後，系統 SHALL 把本次新寫入待審表的案子輸出成 `data/new_this_run.csv`（每次覆蓋），內容包含標題、申請機關、連結、是否疑似舊案與對應舊案 id；本次沒有新案時 SHALL 仍輸出只有表頭的檔案。

#### Scenario: 有新案時報表列出新案

- **WHEN** 本次有 3 筆新案寫入待審表
- **THEN** `data/new_this_run.csv` 有 3 列資料，跟待審表中本次 first_seen_at 的列一致

#### Scenario: 沒有新案時報表為空

- **WHEN** 本次沒有任何新案
- **THEN** `data/new_this_run.csv` 只有表頭，不保留上次的內容

### Requirement: 審核通過寫入正式表

系統 SHALL 提供一個操作：把指定的待審記錄寫入 `subsidies`，同時把該筆待審的狀態改為 approved、`reviewed_at` 記錄當下時間；另提供把待審記錄改為 rejected 的操作。兩者都 SHALL 在單一交易內完成，並只接受 status＝pending 的記錄。

#### Scenario: 核准後出現在正式表

- **WHEN** 對一筆 pending 的待審記錄執行核准
- **THEN** `subsidies` 多出一筆內容相同的列，該待審記錄 status＝approved、reviewed_at 有值

#### Scenario: 不能重複核准

- **WHEN** 對一筆已經 approved 或 rejected 的記錄執行核准
- **THEN** 操作被拒絕並回報錯誤，`subsidies` 不變

