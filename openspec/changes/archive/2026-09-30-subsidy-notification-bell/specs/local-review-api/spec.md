## ADDED Requirements

### Requirement: 已審核通過清單查詢

本機開發 API SHALL 提供端點回傳所有 `status = approved` 的待審記錄，依 `reviewed_at` 由新到舊排序，每筆至少包含標題與 `reviewed_at`；此端點僅供讀取，MUST NOT 產生任何寫入或狀態變更。

#### Scenario: 回傳已審核通過清單

- **WHEN** 待審表中有數筆 status=approved 的記錄
- **THEN** 端點回傳這些記錄的標題與 reviewed_at，依審核時間新到舊排序

#### Scenario: 沒有已審核通過的記錄

- **WHEN** 待審表中沒有任何 status=approved 的記錄
- **THEN** 端點回傳空清單，而非錯誤
