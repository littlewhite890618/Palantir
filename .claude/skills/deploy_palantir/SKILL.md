---
name: deploy_palantir
description: 當要把 Palantir React 前端發布到 GitHub Pages（更新線上網站）時使用。一個指令完成 build + 安全掃描 + 推送到公開 repo palantir。不碰密碼，只搬已加密的產物。
---

# deploy_palantir — 發布前端到 GitHub Pages

## 用途
把 `React/` build 出來，安全掃描後 force-push 到公開 repo `tianhwaservice/palantir`。
GitHub Pages 偵測到變動會自動重新發布，約 1-2 分鐘後線上更新。

線上網址：`https://tianhwaservice.github.io/palantir/`

架構背景見 `md/PALANTIR_SPEC.md` 的「部署架構」章節。

## 執行
```bash
python .claude/skills/deploy_palantir/scripts/deploy.py
```
不需要任何參數，也**不需要密碼**（只搬 build/ 裡已加密的產物）。

## 更新線上資料的完整流程（兩個指令）
```bash
# 1. 資料有變動時，先重新匯出（這支才要密碼）
python .claude/skills/export_subsidies/scripts/export_subsidies.py

# 2. build + 發布
python .claude/skills/deploy_palantir/scripts/deploy.py
```
> 若只改前端程式、資料沒變，可以跳過第 1 步，只跑第 2 步。

## 它做的三件事
1. **`npm run build`** — 產生 `React/build/`（react-scripts 會先清空 build/，含 .git）
2. **安全掃描**（發布不可逆，從嚴；任一項失敗就中止、不推送）：
   - `index.html`、`subsidies.enc.json` 存在
   - `subsidies.enc.json` 是合法信封（含 salt/iv/data/iterations），不是明文
   - build 內無 `.env`、無 `.py`、無 `src/`
   - 全檔無 `password123` / DB 密碼字串
3. **發布** — 在 build/ 內 fresh `git init` → 單一 commit → `push -f`

## 關鍵設計
- **每次 fresh init + force-push**：發布 repo 永遠只有一個 commit，不累積歷史。
  因為加密檔每次匯出都會因新 salt/IV 全變，git 無法差異壓縮，留歷史會爆
  （1000 筆 × 每日推 ≈ 500MB/年）。真正的版本紀錄在主 repo。
- **不碰密碼**：加密是 export_subsidies 的事，這支只搬產物。
- **git 身分**沿用全域設定；**推送認證**沿用首次手動 push 已快取的憑證，不需重登。

## 前置條件（一次性，已完成）
- 公開 repo `tianhwaservice/palantir` 已建立
- 該 repo Settings → Pages 已啟用（Source: main branch, / root）
- 首次已手動 push 過，GitHub 憑證已快取

## 更新頻率建議
批次更新——爬蟲跑完一輪、或改好一批資料再發布一次，不要改一筆推一次。
每次 push 後 GitHub 要 1-2 分鐘重建，且同事要 F5 才看到新資料。

## 已知限制
- **架構天花板**：約 2000 筆 / 3MB 是「一次載入全部」的舒適上限，超過要改分批載入。
- Pages 設定若被關掉，要回 repo Settings → Pages 重新啟用。
