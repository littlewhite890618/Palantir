# Palantir 前端（React）導覽

補助案查詢平台的前端。這份檔案會在你於 `React/` 內工作時自動載入，作用是索引——列出有哪些文件、各自記什麼、什麼時候該去讀，細節不重複貼在這裡。

## 文件索引

| 檔案 | 用途 | 何時該讀 |
|---|---|---|
| [`../md/PALANTIR_SPEC.md`](../md/PALANTIR_SPEC.md) | **HomePage 篩選規格權威來源**：機關/金額/期限三個篩選維度的分類規則、AND/OR 邏輯、資料欄位背景（`category` 實際是機關別、`amount`/`deadline` 是自由文字）、瀏覽/搜尋共用分頁設計 | 要跑/改 `HomePage.js` 的篩選/分頁邏輯前必讀 |
| [`../md/DEPLOY_FRONTEND.md`](../md/DEPLOY_FRONTEND.md) | **前端部署權威來源**：資料如何從本地 DB 加密後上到 GitHub Pages、密碼閘/解密/`HashRouter`/`homepage`/`noindex` 為何這樣設計、**日常更新線上資料的兩個指令** | 要 build/發布、更新線上資料，或碰 `subsidyService.js`/`PasswordGate.js`/`App.js` 前必讀 |
