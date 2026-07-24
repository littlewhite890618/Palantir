---
name: ddg_search_notice_pdf
description: 當爬蟲直接抓不到申請須知、想改用 DuckDuckGo 搜尋（機關,計畫名稱）配對來找須知 PDF 時使用。屬封存的歷史工具，是搜尋補救路線而非逐站遍歷。
---

# ddg_search_notice_pdf — DuckDuckGo 搜尋須知 PDF

## 用途
當站內爬取（`probe_classify_sites`／`deep_crawl_find_notice`）都找不到申請須知時，改用
DuckDuckGo 搜尋「機關 + 計畫名稱 + 申請須知」，看能否從搜尋結果命中官方 PDF。是搜尋補救路線，
不是逐站遍歷。

## 現況（重要）
⚠️ **封存的歷史工具（非現行 pipeline）**。需先有（機關,計畫名稱）配對清單才能執行。

## 執行
```bash
python scripts/ddg_search_notice_pdf.py --batch 1 --total 4   # 分批跑，第1批共4批
python scripts/ddg_search_notice_pdf.py --test                 # 只跑前3列測試
```
結果增量寫入 `data/search_hits.csv`。

## 依賴
```bash
pip install ddgs   # 或舊版 pip install duckduckgo_search
```

## 已知坑
- DuckDuckGo 有速率限制，大量查詢需注意間隔（程式內建 `time.sleep`）與分批（`--batch/--total`）
- 搜尋結果需自行判斷是否為官方站（`gov.tw`）+ PDF/DOC 連結，不能照單全收

## 相關 Skill
- 更直接的爬取方式 → `deep_crawl_find_notice`
