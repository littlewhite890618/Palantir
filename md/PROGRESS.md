## 1. 前置｜確認開發方向（9/14–9/18）

- [x] 1.1 調整 `PROGRESS.md`，對齊實際進度
- [x] 1.2 核對 S1 搜尋／S2 篩選／S3 詳細頁程式邏輯與 `PALANTIR_SPEC.md` 一致，無需改動
- [ ] 1.3 補進 `PALANTIR_SPEC.md`：`HomePage.js` 的 sessionStorage 還原行為（返回時還原關鍵字/篩選/頁碼）

## 2. N. 通知模組（9/16–10/6）

- [ ] 2.1 排程：Windows 工作排程器呼叫 `run_pipeline.bat`（設定步驟見 README，執行時間待定）
- [x] 2.2 增量偵測 ＋「本次新增」報表：新案進待審表 `subsidies_pending`＋`data/new_this_run.csv`
- [x] 2.3 告警（只寫檔）：`data/run_summary.json`＋`data/alerts.log`（管線失敗、萃取失敗 ≥10%）
- [x] 2.4 驗證：測試庫實測 165 筆 → 新案 6、跳過 154、疑似舊案 2，正式表未變動
- [x] 2.5 N1 新案上線通知（9/16–9/30）：管理台 `/#/admin` 審核頁（`subsidy-review-page`）＋搜尋器通知鈴鐺／未讀徽章／popover（`subsidy-notification-bell`）；點 popover 導向 `/new-cases` 占位頁，清單內容屬 N2
- [x] 2.6 N2 新案列表查看（9/30–10/6）：`/new-cases` 列出「最近一批通知」的審核通過新案（OpenSpec `new-cases-list`）；卡片重用搜尋頁 SubsidyCard，可點進詳細頁、可收藏

## 3. C. 行事曆模組（10/7–10/30）

- [x] 3.1 C1 行事曆查看（10/7–10/21）：一覽補助案截止日的日曆（OpenSpec `subsidy-deadline-calendar`，與 3.3 合併交付；2026-10-01 上線）
- [x] 3.2 C1 前置：`deadline` 日期解析與正規化（自由文字、多為民國年）——已在搜尋頁期限篩選提前完成並發佈（2026-09-29 修正 `getDeadlineBucket`，同款邏輯可供 C1 行事曆直接引用）
- [x] 3.3 C2 到期計畫案查看（10/22–10/30）：查看即將到期或已截止的計畫案——併入 3.1：行事曆點日期彈出當日截止案清單，可進詳細頁

## 4. 交付

- [ ] 4.1 Demo 演練＆交付（10/30）
