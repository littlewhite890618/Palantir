## MODIFIED Requirements

### Requirement: 已審核通過清單查詢

本機開發 API SHALL 提供端點回傳所有 `status = approved` 的待審記錄，依 `reviewed_at` 由新到舊排序；每筆 SHALL 包含足以呈現補助案卡片的完整內容欄位（標題、申請機關、補助金額、申請截止日期、描述、連結等）與 `reviewed_at`，並 SHALL 附上該案在正式表 `subsidies` 的對應 id（以申請機關與連結比對，與增量偵測使用同一組身分 key）供前端連往詳細頁；在正式表找不到對應資料時，該欄位 SHALL 為空而非讓整筆消失。此端點僅供讀取，MUST NOT 產生任何寫入或狀態變更。

#### Scenario: 回傳已審核通過清單

- **WHEN** 待審表中有數筆 status=approved 的記錄
- **THEN** 端點回傳這些記錄的完整內容欄位、reviewed_at 與對應的正式表 id，依審核時間新到舊排序

#### Scenario: 正式表找不到對應資料

- **WHEN** 某筆 approved 記錄在正式表沒有相符的（申請機關, 連結）
- **THEN** 該筆仍出現在清單中，對應的正式表 id 為空

#### Scenario: 沒有已審核通過的記錄

- **WHEN** 待審表中沒有任何 status=approved 的記錄
- **THEN** 端點回傳空清單，而非錯誤
