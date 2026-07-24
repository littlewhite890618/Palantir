---
name: find_subsidy_list_page
description: 當要判斷某個政府網址目前是否已經是「補助案列表頁」、若不是要往下鑽一層找出列表頁時使用。屬封存的歷史工具。
---

# find_subsidy_list_page — 找補助案列表頁

## 用途
判斷 URL 目前是否已是補助案列表頁；若不是，往下鑽一層找出「點進去直接是補助案列表」的頁面，
回傳建議 URL。用於 `probe_classify_sites`／`deep_crawl_find_notice` 找不到須知檔後的補救。

## 現況（重要）
⚠️ **封存的歷史工具（非現行 pipeline）**。原輸入檔（同 `deep_crawl_find_notice`，中文檔名）
已遺失。保留當參考範本。

## 執行（若要重新使用，需先重建輸入 CSV）
```bash
python scripts/find_subsidy_list_page.py --in <輸入CSV> --out <輸出CSV> \
  [--cats "申請系統入口,待人工確認,外部連結彙整"] [--rows 1,2] [--per 8] [--delay 0.6]
```
- `--cats`：只處理指定類別的列（逗號分隔）

## 相關 Skill
- 上游分類 → `probe_classify_sites`
- 上游深鑽 → `deep_crawl_find_notice`
