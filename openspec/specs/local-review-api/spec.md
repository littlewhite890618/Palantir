# local-review-api Specification

## Purpose
定義本機開發 API 對前端提供的行為契約：讀取待審補助案（含疑似舊案內容供比對）、逐筆核准或退回、查詢上次管線執行摘要，以及這支服務只在本機可用的限制。
## Requirements
### Requirement: 只在本機提供服務

本機開發 API SHALL 只監聽本機位址（127.0.0.1），MUST NOT 接受來自其他主機的連線；跨來源請求 SHALL 只允許本機前端的來源。

#### Scenario: 同網段其他電腦連不上

- **WHEN** 同一區域網路的另一台電腦以本機的區域網路 IP 連線本服務
- **THEN** 連線被拒絕，無法讀取待審清單，也無法送出審核

#### Scenario: 本機瀏覽器可正常使用

- **WHEN** 使用者在本機瀏覽器開啟本機前端並呼叫本服務
- **THEN** 請求成功，回應帶有允許該來源的跨來源標頭

### Requirement: 待審清單

系統 SHALL 提供端點回傳待審補助案清單，預設只含 status＝pending 的案子，依 `first_seen_at` 由新到舊排序，每筆包含補助案全部內容欄位、`first_seen_at` 與 `suspected_dup_of`。若某筆有 `suspected_dup_of`，回應 SHALL 一併帶出該舊案在正式表的完整內容，供前端並排比對。

#### Scenario: 回傳待審案與對應舊案

- **WHEN** 待審表有 2 筆 pending，其中 1 筆 `suspected_dup_of` 指向正式表某筆
- **THEN** 回應含這 2 筆的完整內容，且有疑似舊案的那筆另外帶出該舊案的標題、金額、截止日期、連結等內容

#### Scenario: 已審核的不出現在待審清單

- **WHEN** 某筆待審記錄的 status 已是 approved 或 rejected
- **THEN** 該筆不出現在預設的待審清單中

### Requirement: 逐筆核准與退回

系統 SHALL 提供核准與退回兩個端點，各接受一筆待審記錄的 id，行為等同既有的審核操作（核准寫入正式表並標記 approved；退回只標記 rejected）。操作成功 SHALL 回傳成功結果，失敗（id 不存在、已審過、資料庫錯誤）SHALL 回傳錯誤狀態與可判讀的錯誤訊息，且 MUST NOT 造成部分寫入。

#### Scenario: 核准成功

- **WHEN** 對一筆 pending 記錄呼叫核准端點
- **THEN** 回應成功，該案出現在正式表，待審記錄狀態變成 approved

#### Scenario: 重複核准被拒絕

- **WHEN** 對一筆已經 approved 的記錄再次呼叫核准端點
- **THEN** 回應錯誤狀態與說明訊息，正式表內容不變

### Requirement: 執行摘要查詢

系統 SHALL 提供端點回傳最近一次管線執行摘要的內容；摘要檔不存在時 SHALL 回傳「尚無執行紀錄」的結果，而不是錯誤。

#### Scenario: 有執行紀錄

- **WHEN** 管線已執行過並留下摘要
- **THEN** 回應包含該次執行的結束時間與結果

#### Scenario: 從未執行過

- **WHEN** 摘要檔不存在
- **THEN** 回應是「尚無執行紀錄」的成功結果，前端據此顯示提示

### Requirement: 已審核通過清單查詢

本機開發 API SHALL 提供端點回傳所有 `status = approved` 的待審記錄，依 `reviewed_at` 由新到舊排序，每筆至少包含標題與 `reviewed_at`；此端點僅供讀取，MUST NOT 產生任何寫入或狀態變更。

#### Scenario: 回傳已審核通過清單

- **WHEN** 待審表中有數筆 status=approved 的記錄
- **THEN** 端點回傳這些記錄的標題與 reviewed_at，依審核時間新到舊排序

#### Scenario: 沒有已審核通過的記錄

- **WHEN** 待審表中沒有任何 status=approved 的記錄
- **THEN** 端點回傳空清單，而非錯誤

