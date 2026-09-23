
## 文件索引

| 檔案 | 用途 | 何時該讀 |
|---|---|---|
| `EXTRACT_PDF_SPEC.md` | **萃取規格權威來源**：輸入/輸出格式、錨點關鍵字策略、時程6型/金額3型、`cn2int()`國字數字支援、NFKC修復CJK相容表意字、2026-07-20 漏抓重跑（4種狀態→67/68補回）、環境限制 | 要跑/改 `extract_schedule_amount.py`、`rerun_missing.py` 前必讀 |
| `DEV_WORKFLOW.md` | 判斷「執行型 vs 設計型」需求、何時該開需求規格文件、文件如何迭代更新 | 每次要開始一個新功能/改動前，判斷要不要先開文件討論時 |
| `PALANTIR_SPEC.md` | **Palantir 前端（React/）規格權威來源**：HomePage 篩選規則（機關/金額/期限）、瀏覽/搜尋共用分頁設計、資料欄位背景、收藏功能設計、詳細頁設計。**文末另含「Palantir 後端規格」**：`subsidy_crawler/` 補助案自動抓取管線（28 站分批 A/B/C、公告發布日過濾、重用 `extract_schedule_amount` 萃取引擎、四階段 P1–P4、先獨立存放） | 要跑/改 `React/` 頁面邏輯、或後端抓取管線前必讀 |
| `PROGRESS.md` | **功能模組進度追蹤**：N 通知模組、C 行事曆模組、交付的任務清單（`- [ ]` 待辦框）與各模組日期；格式比照 openspec `tasks.md`（群組＋單行任務） | 要看/更新目前做到哪、接下來做什麼時 |
| `DEPLOY_FRONTEND.md` | **前端部署權威來源**：定案架構（PostgreSQL→gzip→加密 JSON→GitHub Pages 靜態站，零對外開放 port）、已排除方案與原因（Cloudflare Tunnel/ngrok/VPS/Google Sheet 為何不用）、匯出/解密/發布各元件、**日常更新線上資料的流程（兩個指令）**、備份與交易慣例、架構天花板 | 要跑/改部署、更新線上資料、或討論上線方式前必讀。相關 skill：`export_subsidies`、`deploy_palantir` |
| `RECORD.md` | **去重驗證紀錄**：165筆(舊)/168筆(整合萃取前全文比對機制後)兩版本的總筆數、疑似重複逐群分析與原因、本輪實際修改項目（冒號正規化、申請類別守門清單擴充、`_fulltext_prefilter`）、去重後合理筆數範圍估算、待辦事項 | 要查/比對 `subsidy_crawler` 去重測試結果、追查某組資料為何沒被去重、或接續補齊已知缺口前必讀 |

