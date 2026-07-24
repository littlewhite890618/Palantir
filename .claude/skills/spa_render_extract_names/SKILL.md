---
name: spa_render_extract_names
description: 當一般 requests 抓不到補助案名稱（403 或 SPA 頁面需 JS 渲染）、需要用真瀏覽器 render 頁面才能擷取計畫名稱時使用。屬封存的歷史工具。
---

# spa_render_extract_names — Playwright 補抓 SPA 頁面計畫名

## 用途
用 Playwright（真瀏覽器）render 那些一般 `requests` 抓不到內容的頁面（403 阻擋或 Vue/React SPA），
擷取頁面上的補助案計畫名稱。是 `probe_classify_sites` 的 fix：把原本「找不到計畫名稱」的列，
補抓成功後移到「有計畫名稱」那桶。

## 現況（重要）
⚠️ **封存的歷史工具（非現行 pipeline）**。原輸入檔 `否_無計畫名稱.csv`（中文檔名）已遺失，
需先有 `否_有計畫名稱.csv`／`否_無計畫名稱.csv` 這組檔案才能執行。

## 執行（若要重新使用，需先重建輸入 CSV）
```bash
python scripts/spa_render_extract_names.py
```
需求：`pip install playwright` + `playwright install chromium`
輸出：把補抓成功的列從「無計畫名稱」移到「有計畫名稱」CSV，兩檔皆覆寫。

## 判斷邏輯
- 正面關鍵字（`ITEM_KW`）：補助/獎助/補貼/津貼/獎勵/計畫/徵件/徵選/申請/方案/要點
- 排除關鍵字（`NEG`）：支付或接受/施政計畫/業務統計/旅費/出國/考察/利益衝突…等非補助案的雜訊

## 相關 Skill
- 上游：`probe_classify_sites`
- 若 Playwright 也抓不到，可考慮 `ddg_search_notice_pdf` 改用搜尋補救
