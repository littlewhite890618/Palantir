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
