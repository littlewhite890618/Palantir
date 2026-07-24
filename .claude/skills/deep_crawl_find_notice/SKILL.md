---
name: deep_crawl_find_notice
description: 當要對政府機關網址做多層深鑽（BFS，往下鑽最多N層）直到找到「申請須知」PDF為止時使用。是探測階段的主力工具，屬封存的歷史工具。
---

# deep_crawl_find_notice — 階段0 深鑽找申請須知（主力）

## 用途
對每個 URL 做 BFS 往下鑽（最多 `--depth` 層），直到某頁找到「申請須知」PDF 就記錄
PDF網址 + 所在頁網址（=更新後網址）。是探測階段撈得最深、命中率最高的工具。

## 現況（重要）
⚠️ **封存的歷史工具（非現行 pipeline）**。原輸入檔 `政府官方平台資料庫_整理版v5.csv`
（中文檔名）已遺失。歷史結論：站內能穩定抓到申請須知檔的僅個位數，多數補助案沒有可下載的須知檔，
已改用人工整理清單。保留當「多層深鑽找檔」邏輯的參考範本。

## 執行（若要重新使用，需先重建輸入 CSV）
```bash
python scripts/deep_crawl_find_notice.py --in <輸入CSV> --out <輸出CSV> \
  [--rows 4,7] [--depth 3] [--per 6] [--budget 25] [--max-ext 2] [--delay 0.7]
```
- `--rows`：只跑指定列 index，測試用
- `--depth`：鑽取層數；`--per`：每層跟進連結數；`--budget`：每列最多造訪頁數；`--max-ext`：外部網域跳轉上限

## 核心能力（見程式內註解）
- 每列鑽到底，不因網站類別預先跳過
- 跟外部官網（網址：後的連結、錨文字為URL的連結），限官方網域，每列最多2次外部跳轉防亂晃
- 掃 `data-name`/`data-file`/`title` 等屬性，不只 `<a>` 文字
- 認 Google Drive/Dropbox 連結
- LegacyTLSAdapter 救老站 TLS
- 防誤判：須知關鍵字須在檔名、NEG排除非補助須知（契約/議價/兒少/投標）、交叉誤植偵測

## 相關 Skill
- 更前置的分類 → `probe_classify_sites`
- 找不到就退而找列表頁 → `find_subsidy_list_page`
