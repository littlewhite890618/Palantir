# subsidy_crawler

政府補助「申請須知」自動抓取系統（Palantir 後端）。

- 規格：[`../md/PALANTIR_SPEC.md`](../md/PALANTIR_SPEC.md)「Palantir 後端規格」
- 進度：[`../md/PROGRESS.md`](../md/PROGRESS.md)

## 結構
```
common/   共用工具（連線 / 年度 / 找須知 / SQLite / adapter 介面 / 瀏覽器）
sites/    各站 adapter（小抄）
data/     輸出（subsidy.sqlite、notices_*.csv）
run.py    主入口
```

## 怎麼跑
```
python -m subsidy_crawler.run --site kinmen
```
（目前為骨架階段，common/ 與 sites/ 多為 stub，會依 PROGRESS.md 逐步填。）

## 一鍵管線＋排程＋監控

```
python -m subsidy_crawler.pipeline            # 爬蟲 → 萃取 → 去重 → 新案寫入待審表
python -m subsidy_crawler.pipeline --skip-db  # 不碰資料庫
```

資料庫步驟**不會改動正式表 `subsidies`**：用（申請機關, 連結）比對 `subsidies`＋`subsidies_pending`，
只把沒見過的新案寫進待審表 `subsidies_pending`（status=pending）。標題跟同機關、同網域舊案相似度 ≥ 0.85 的會記在
`suspected_dup_of`（疑似網址換掉的舊案）。審核通過才透過 `db.approve_pending(ids)` 寫進 `subsidies`；
`db.reject_pending(ids)` 退回後，同一個案子之後再抓到也會跳過。

每次執行留下的檔案（都在 `data/`，不進版控）：

| 檔案 | 內容 |
|---|---|
| `run_summary.json` | 最新一次執行摘要（成功/失敗、耗時、爬到/萃取/新增筆數），每次覆蓋 |
| `alerts.log` | 告警，只追加：管線失敗、萃取失敗比例 ≥ 10% |
| `new_this_run.csv` | 本次新寫入待審表的案子（沒有新案也會有表頭），每次覆蓋 |
| `pipeline_run.log` | `run_pipeline.bat` 附加的完整輸出 |

驗證時可用環境變數 `POSTGRES_DB=<測試庫名>` 指到別的資料庫，不動正式資料。

### Windows 工作排程器設定

排程入口是 repo 根目錄的 `run_pipeline.bat`（輸出附加到 `data/pipeline_run.log`，並回傳管線的 exit code）。
一次完整執行約 4.5 小時，執行時間請自行決定（電腦需開機、docker 的 postgres 需啟動）。

1. 開「工作排程器」→ 右側「建立工作」（不是「建立基本工作」）
2. 一般：名稱填 `SubsidyPipeline`；勾「不論使用者登入與否均執行」
3. 觸發程序：新增 → 依需求設定每週／每天與時間
4. 動作：新增 → 啟動程式 → 程式填 `C:\Users\evalu\Desktop\JOHNNY\n8ntest\run_pipeline.bat`，
   「開始位置」填 `C:\Users\evalu\Desktop\JOHNNY\n8ntest`
5. 設定：勾「如果錯過排程的開始時間，儘快執行工作」；「如果工作執行超過下列時間，就停止」設 8 小時
6. 存檔後在清單上按右鍵「執行」手動跑一次，結束後看「上次執行結果」是否為 `0x0`，並檢查 `data/run_summary.json`

## 本機開發 API 與新案審核頁

```
python -m subsidy_crawler.dev_api      # 本機 API（127.0.0.1:8001）
docker compose up react                # 前端 localhost:3000 →「新案審核」
```

`dev_api.py` 的端點（**只監聽 127.0.0.1**：沒有任何認證，加上審核寫入後，綁 `0.0.0.0`
等於同網段的人都能改資料庫；瀏覽器跑在本機，前端不受影響）：

| 端點 | 用途 |
|---|---|
| `GET /api/subsidies` | 正式表全部內容（未加密），本機前端資料來源 |
| `GET /api/pending` | 待審新案；有疑似舊案時一併帶出該舊案內容供並排比對 |
| `GET /api/approved` | 已審核通過清單（含 reviewed_at），供搜尋器通知鈴鐺算未讀數 |
| `GET /api/run-summary` | 最近一次管線執行摘要；沒跑過回 `{"exists": false}` |
| `POST /api/pending/approve` | `{"id": n}` 核准 → 寫入正式表、標記 approved |
| `POST /api/pending/reject` | `{"id": n}` 退回 → 標記 rejected（不寫正式表） |

審核頁在**管理台** `localhost:3000/#/admin`：獨立版面（深色標題列，不是搜尋器的導覽列），
逐筆「通過」「退回」，點一列展開看完整內容，疑似舊案會把新案與既有案左右並排比對。
搜尋器那邊沒有任何通往管理台的連結，要自己輸入網址。

**只在本機開發模式存在**：是否打包由 `NODE_ENV` 決定（正式 build 時壓縮器會把管理台的
程式碼與字串整段刪除），是否註冊路由再由 `REACT_APP_LOCAL_API_URL` 把關（只有
docker-compose 的 react 服務會設）。正式發布版本裡搜尋不到審核相關字串，也沒有任何
寫入端點的呼叫。
