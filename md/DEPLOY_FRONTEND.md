# Palantir 前端部署架構

補助案查詢平台（`React/`）的部署方式與維運流程。**已完成、網站已上線**：
`https://tianhwaservice.github.io/palantir/`

這份文件的重點是**為什麼選這條路、排除了哪些路**，避免下次要調整時又把所有選項
重新討論一遍；以及**日常怎麼更新資料上線**。前端頁面本身的規格見 [`PALANTIR_SPEC.md`](PALANTIR_SPEC.md)。

## 使用情境與限制條件

| 條件 | 內容 |
|---|---|
| 使用者 | 公司內部 1-3 人，偶爾查看 |
| 存取位置 | **同事可能在辦公室外**（所以純內網方案不可行） |
| 機器 | 24 小時開著沒問題 |
| 預算 | 以免費為主 |
| 需求範圍 | **老闆的需求就是「用前端查詢與篩選補助案」**——不需要線上編輯資料、不需要即時同步 |
| 存取控制 | **要擋住外人，但明確不寫帳號系統** |
| 資料性質 | 補助案本身是**政府公開資訊**；要保護的是「整理成結構化清單」這份成果 |

## 已評估但排除的方案

| 方案 | 排除原因 |
|---|---|
| GCP | 使用者決定排除 |
| Railway | 30 天試用後 **$1/月起**（用量計費），不是永久免費；且沒有網路層隔離能力 |
| Render | **免費層閒置約 15 分鐘會休眠**，喚醒要 30-60 秒。對「前端打 API 拿資料」的架構是硬傷 |
| **Cloudflare Tunnel + Access**（前一版定案） | 方案本身很好（免費、免固定 IP、不開 port、Access 50 人免費），**卡在網域**：Access 不支援 `trycloudflare.com` 臨時網址，必須有自有網域且 DNS 託管在 Cloudflare。而公司的 GoDaddy 網域有多個子網域在用，**改 nameserver 是整個網域一起搬**（免費層不支援只委派子網域：partial CNAME 要 Business、subdomain zone 要 Enterprise），有搞爛公司信箱的風險 |
| **ngrok** | 免費層 1 GB/月、有警告插頁；**認證只涵蓋 3 個活躍使用者**且需 Traffic Policy（Pay-as-you-go 以上）→ 實務上等於無認證。且要能用就得**把沒有身分驗證的 n8n 一起對外開放**，風險過高 |
| GoDaddy VPS | 要月租；**登入保護要自己寫**；且爬蟲從機房 IP 出去**容易被政府網站封鎖**（目前從辦公室 IP 出去看起來像正常使用者） |
| 自行開 port + DNS 指向辦公室 | 需固定公網 IP、要在路由器開 443 對全世界。以現況（`password123`、n8n 無驗證）等於把資料庫放到大街上 |
| Google Sheet 當資料來源 | 釐清後老闆**不需要用試算表看/改資料**，Sheet 只是「把資料送到靜態站」的手段 → 是多餘環節。直接 DB→JSON 少一個會壞的地方，也避開 CSV 換行/逗號解析與跨網域問題 |
| 全本地、不對外 | 同事在外面連不到 |

> 註：先前版本曾以「未來要加帳號」為由排除靜態站方案。該前提已變更——帳號系統現階段
> 明確不做，且靜態站可用「資料加密」達成存取控制，故重新評估後採用。

## 定案架構

```
本地 PostgreSQL（subsidies 表，約 200 筆）
        │
        │ export_subsidies（匯出 → gzip 壓縮 → AES-GCM 加密，要密碼）
        ↓
   React/public/subsidies.enc.json
        │
        │ deploy_palantir（npm run build → 安全掃描 → force-push）
        ↓
   公開 repo tianhwaservice/palantir ──→ GitHub Pages
        │
        ↓
   同事瀏覽器（輸入密碼 → Web Crypto 解密 → 解壓）
```

**設計決定 1 — 為什麼是靜態站**：資料約 200 筆、原始 JSON 約 1 MB，gzip 後約 210 kB、
加密後約 280 kB，**當靜態檔一次送出就好，不需要後端**。老闆的需求（查詢、篩選）全部是
前端行為，資料也不是即時變動的。為這個規模架一整套 API + 通道是過度設計。

**設計決定 2 — 零對外開放**：本機**不需要開任何 port、不需要通道、不需要網域**。
資料是單向推出去的，所以 `password123` 的 PostgreSQL 與**沒有身分驗證的 n8n 永遠碰不到
網路**。這比 Tunnel／ngrok／開 port 任何一種都安全，因為攻擊面直接是零。

**設計決定 3 — 用「加密資料」而不是「密碼檢查畫面」**：在前端寫 `if (輸入 === "密碼")`
是假防護——密碼寫在 JS 裡、F12 就看到，而且資料早已下載到瀏覽器。改成**把 JSON 本身用
AES-GCM 加密**，沒密碼的人拿到的是亂碼，跳過畫面也沒用，因為站上不存在未加密的資料。
**網站本身不知道正確密碼**，它只是拿輸入去試解密，失敗就是失敗。

代價（已知並接受）：**共用密碼、無法針對個別同事撤銷**；換密碼要重新匯出發布。
以 1-3 人內部使用可接受。

## 組成元件（皆已完成）

### 匯出：`export_subsidies` skill
`.claude/skills/export_subsidies/scripts/export_subsidies.py`
- `psycopg2` 連 `localhost:5434` / `palentir_test_db`，帳密讀 `.env`（**不寫死**）
- `SELECT * FROM subsidies`，date/datetime 轉 ISO 字串（前端 `new Date()` 與期限篩選靠這個）
- **先 gzip 壓縮，再 AES-GCM 加密**（順序不可反：加密後是高亂度資料，再壓壓不動）
- PBKDF2 從密碼派生金鑰（200000 次迭代，兼顧防暴力破解與瀏覽器解密速度）
- **密碼從環境變數 `SUBSIDY_PASSWORD` 或互動輸入取得**，絕不寫進檔案或 commit
- 輸出 → `React/public/subsidies.enc.json`（CRA 的 `public/` 是「原樣複製區」，build 時原封複製）

### 前端：解密與密碼閘
| 檔案 | 作用 |
|---|---|
| `services/subsidyService.js`（取代 n8nService） | 讀 `subsidies.enc.json` → PBKDF2 → AES-GCM 解密 → `DecompressionStream` 解壓 → JSON。全用**瀏覽器內建 Web Crypto API，不裝任何套件**。維持 `getAllSubsidy()` 介面不變 |
| `components/PasswordGate.js` | 解密成功前不渲染任何內容；密碼記在 `localStorage`（永久記住），失效時自動清除並跳回輸入畫面 |
| `components/Navbar.js` | 🔒 登出鈕（清密碼 + 清記憶體快取）+「資料更新於」（讀信封明文 `exported_at`） |
| `App.js`：`HashRouter` | 網址 `/#/subsidy/123`。GitHub Pages **沒有後端把路徑導向 `index.html`**，用 BrowserRouter 會讓詳細頁重新整理 404 |
| `package.json` 的 `homepage` | 指向 `https://tianhwaservice.github.io/palantir`。不設會導致 build 後 JS/CSS 路徑全錯、白畫面 |
| `public/index.html` 的 `noindex` | 擋搜尋引擎索引（逐頁生效，不受子路徑影響）。⚠️ **不要加 `robots.txt`**——子路徑部署下根目錄不歸本專案管，不會被讀取，留著只製造「已處理」假象 |

**關鍵**：`getAllSubsidy()` 介面維持不變，所以 `HomePage` / `FavoritesPage` /
`SubsidyDetailPage` **完全不用改**；`favoritesService.js`（localStorage）也原封不動可用。

**效能決定**：`subsidyService.js` 內有記憶體快取（`cachedRows`），解密一次後切頁直接回傳。
PBKDF2 是刻意慢的，不快取的話每次換頁都要重付約 300-400ms。**只放記憶體、不放 localStorage**
——寫進磁碟等於讓明文資料躺在硬碟上，加密就白做了。

### 發布：`deploy_palantir` skill
`.claude/skills/deploy_palantir/scripts/deploy.py`
1. `npm run build`
2. **安全掃描**（發布不可逆，從嚴；任一項失敗就中止）：加密檔是合法信封（非明文）、
   build 內無 `.env`／`.py`／`src/`、全檔無 `password123`／DB 密碼字串
3. 在 `build/` 內 fresh `git init` → 單一 commit → `push -f` 到 `tianhwaservice/palantir`

**設計決定 — 單一 commit 覆蓋、不留歷史**：加密檔每次匯出都因新 salt/IV 全變，git 無法
差異壓縮，逐次累積會爆（1000 筆 × 每日推 ≈ 500 MB/年）。force-push 單一 commit 後，
發布 repo 永遠只有一份檔案大小。真正的版本紀錄在主 repo 的 commit。

**為什麼要獨立的公開 repo**：GitHub 免費方案的 Pages 只能從公開 repo 發布。主 repo
`ProjectPalentir` 維持 private（含爬蟲、skills、`.env`、設定），只把 build 產物推到公開的
`palantir`。build 產物不含原始碼與密碼，公開是安全的。

## 日常維運

### 更新線上資料（最常做的操作）
資料庫改了東西後，兩個指令讓線上更新：
```bash
# ① 匯出（要輸入正式密碼——與同事在用的同一組）
python .claude/skills/export_subsidies/scripts/export_subsidies.py
# ② build + 發布（不用密碼）
python .claude/skills/deploy_palantir/scripts/deploy.py
```
- 若只改前端程式、資料沒變 → 可跳過 ①，只跑 ②
- push 後 GitHub Pages 約 1-2 分鐘重建；**同事要 F5 重新整理**才看到新資料
- 建議**批次**更新（改一批再推一次），不要改一筆推一次

### 改資料的安全流程（本專案慣例）
直接改資料庫時，先 `pg_dump` 備份 → 用 `BEGIN…COMMIT` 交易包住 → 先 `SELECT` 預覽
確認無誤才 COMMIT。備份防「改錯內容」，交易防「改到一半」。

### 備份
本機資料庫沒有人會自動幫你備份。改動前後用：
```bash
docker exec postgres pg_dump -U admin palentir_test_db > 備份檔.sql
```
（尚未做定期自動排程；目前是每次改資料前手動備份。）

## 架構天花板
實測每筆約 1.4 KB（加密壓縮後）。約 **2000 筆 / 3 MB** 是「一次載入全部、前端過濾」的
舒適上限，超過就該改成分批載入、或回頭做 API（FastAPI）。目前約 200 筆，短期無虞。

## 未來預留（現在不做）
- **帳號資料表 + 站內登入**：屆時 `services/favoritesService.js` 內部實作從 localStorage
  換成呼叫後端 API（維持同樣三個函式介面），`SubsidyCard`／`FavoritesPage`／`HomePage`
  都不用改。
- **Cloudflare Pages + Access**：理論上可保護 `*.pages.dev` 且**可能不需自有網域**，
  若成立就能換成真正的 Google 帳號登入、取代共用密碼。查到的資料互相矛盾（官方文件寫
  網域須為帳號下的有效 zone），**未經實測，不列入計畫**。
- **後端取代 n8n**：用 Python/FastAPI 提供 API + 排程爬蟲，取代 n8n 現在做的 ETL 與 API 兩件事。
