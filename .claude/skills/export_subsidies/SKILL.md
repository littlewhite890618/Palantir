---
name: export_subsidies
description: 當要把 subsidies 資料表匯出成加密 JSON、給 GitHub Pages 靜態站（Palantir 前端）使用時使用。用密碼加密，前端輸入密碼才解得開。每次要更新線上資料就跑這支。
---

# export_subsidies — 匯出加密資料給靜態站

## 用途
把 PostgreSQL 的 `subsidies` 表整包匯出，gzip 壓縮後用 AES-GCM 加密，
產生 `React/public/subsidies.enc.json`。前端（`React/src/services/subsidyService.js`）
用瀏覽器內建 Web Crypto API 解密。

架構背景見 `md/PALANTIR_SPEC.md` 的「部署架構」章節。

## 執行
```bash
# 用環境變數給密碼（推薦，可寫進發布腳本）
SUBSIDY_PASSWORD="你的密碼" python .claude/skills/export_subsidies/scripts/export_subsidies.py

# 不給環境變數就會互動式詢問
python .claude/skills/export_subsidies/scripts/export_subsidies.py

# 指定輸出路徑（預設 React/public/subsidies.enc.json）
python .claude/skills/export_subsidies/scripts/export_subsidies.py <輸出路徑>
```

DB 連線：帳密讀專案根目錄的 `.env`；host/port 預設 `localhost:5434`，
可用 `POSTGRES_HOST` / `POSTGRES_PORT` 環境變數覆蓋。

## 依賴
- `psycopg2-binary`（連 PostgreSQL）
- `cryptography`（AES-GCM + PBKDF2）

## 輸出格式
```json
{
  "v": 1,
  "kdf": "PBKDF2-SHA256",
  "iterations": 200000,
  "compression": "gzip",
  "salt": "<base64>",
  "iv": "<base64>",
  "data": "<base64 ciphertext||tag>",
  "exported_at": "2026-07-29T14:30:00+08:00"
}
```
`exported_at` 是明文（讓密碼畫面能顯示資料新舊，不解密也讀得到）。其餘皆為密文。

## 實測數據（201 筆）
| 階段 | 大小 |
|---|---|
| 原始 JSON | 1015 KB |
| gzip 後 | 213 KB（20.9%）|
| 加密 + base64（最終檔案）| **277 KB** |

## 關鍵設計（改之前務必先讀）

1. **加密參數必須與前端 `subsidyService.js` 完全一致**
   （迭代數 200000 / salt 16B / IV 12B / AES-256-GCM / SHA-256）。
   對不上的症狀是「解密失敗」，跟「密碼打錯」**外觀完全相同**、無從分辨。
   要改就兩邊一起改，改完務必重跑下面的驗證。

2. **先壓縮再加密，順序不能反。** 加密後的資料是高亂度的，再壓縮完全壓不動。

3. **日期一律轉 ISO 字串（`YYYY-MM-DD`）。** JSON 沒有日期型別，不轉會直接
   `TypeError`；而且前端 `HomePage.js` 的 `getDeadlineBucket()` 用
   `new Date(deadline)` 解析，只有 ISO 保證跨瀏覽器一致。換成 `2026/7/29` 或
   `29/07/2026` 會讓「期限」篩選壞掉（後者還會靜默地把日期解析錯，不報錯）。

4. **密碼只從環境變數或互動輸入取得**，絕不寫進檔案、絕不進 commit。

5. **產出檔已列入 `.gitignore`**——每次匯出內容全變，進版控會讓 repo 快速膨脹。
   要用就重跑這支。

6. **本環境 console 是 cp950，印中文會報錯**，所以程式訊息一律英文
   （見 `extract_schedule_amount/SKILL.md` 已知坑 #3）。

## 驗證方式
改動加密邏輯後，一定要跑跨語言驗證（Python 加密 → JS 解密），不要等前端寫完才發現對不上：

```bash
# 1. 匯出
SUBSIDY_PASSWORD="test-1234" python .claude/skills/export_subsidies/scripts/export_subsidies.py

# 2. 用 Node 的 Web Crypto（與瀏覽器同一套 API）解解看
node verify_decrypt.mjs React/public/subsidies.enc.json "test-1234"   # 應成功
node verify_decrypt.mjs React/public/subsidies.enc.json "wrong"       # 應失敗

# 3. 確認沒有明文洩漏
grep -c "補助" React/public/subsidies.enc.json   # 應為 0
```

## 已知限制
- **共用密碼**，無法針對個別使用者撤銷；換密碼要重新匯出 + 重新發布。
- 查詢回傳 0 筆時程式會中止（拒絕發布空資料），避免資料庫沒開卻覆蓋掉線上好的資料。
