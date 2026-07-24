---
name: probe_classify_sites
description: 當要對一批政府機關網址做初步探測分類——測 HTTP 狀態、技術類型、頁面型態、站內有無申請須知 PDF、可自動化程度時使用。這是探測階段（階段0）的起手式，屬封存的歷史工具。
---

# probe_classify_sites — 階段0 探測分類

## 用途
對每個政府機關 URL 做初步探測：HTTP 狀態、技術類型（靜態/SPA等）、頁面型態、
**是否含申請須知 PDF**、可自動化程度分類。**不抓補助內容，只分類**，是後續深鑽（`deep_crawl_find_notice`）的前置步驟。

## 現況（重要）
⚠️ 這是 **2026-07 探測階段（非現行 pipeline）** 的封存工具。原輸入檔
`政府官方平台資料庫_整理版v4.csv`（中文檔名）已隨環境遺失。目前 gov_subsidy 的主線任務已改用
人工整理的 stage2/3/4 清單直接餵給 `extract_schedule_amount`，**不再需要重跑這支**，
保留是當作探測邏輯的參考範本。

## 執行（若要重新使用，需先重建輸入 CSV）
```bash
python scripts/probe_classify_sites.py --in <輸入CSV> --out <輸出CSV> [--limit N] [--rows 1,2,3] [--delay 1.5] [--force]
```
輸入需含機關名稱/網址欄位。輸出 `probe_result.csv`。

## 已知坑
- 部分機關類別會被 `SKIP_CATEGORIES` 跳過，需 `--force` 才會硬爬
- 老政府站 TLS 問題同樣需要 LegacyTLSAdapter（程式內已內建）

## 相關 Skill
- 找到「是」之後要往下鑽找 PDF → `deep_crawl_find_notice`
- 對「否」的列找補助案列表頁 → `find_subsidy_list_page`
