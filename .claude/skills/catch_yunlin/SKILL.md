---
name: catch_yunlin
description: 當要下載雲林縣政府網站上的申請須知 PDF、但一般 requests 被 Cloudflare 擋下（403/驗證頁）時使用。用真瀏覽器（Selenium 非 headless + 反偵測設定）繞過防護。
---

# catch_yunlin — 雲林 Cloudflare 繞道下載

## 用途
雲林縣政府網站（`ws.yunlin.gov.tw`）對一般 `requests`／無頭瀏覽器的請求會被 Cloudflare
擋下。這支開一個**非 headless**、帶反偵測設定的 Chrome，先造訪首頁熱身、再進下載頁，
真的觸發瀏覽器下載後把檔案複製進共用快取 `md/data/pdf_cache/`。

## 現況（重要）
- **自包含**：不依賴 `extract_schedule_amount` skill 的路徑，inline 了同款 `safe_name()` 命名邏輯，可獨立搬動/執行。
- **目前寫死單一目標**：URL/部門/檔名（雲林「地方型SBIR申請須知」）都寫在檔案開頭。要抓雲林縣的**別份** PDF，需先修改這三個變數，不是通用參數化工具。
- 下載進的快取路徑跟 `extract_schedule_amount` 共用（`md/data/pdf_cache/`），命名規則一致，抓完之後主引擎重跑會直接吃到快取、不重抓。

## 執行
```bash
python scripts/_yunlin.py
```
成功會印 `DOWNLOADED size=... -> <檔名>.pdf`；失敗印 `NO FILE. title=... current=...`（可用來判斷是否被導去驗證頁）。

## 依賴
```bash
pip install selenium
```
需本機安裝 Chrome 瀏覽器（Selenium 4.6+ 會自動處理 driver，不需另外裝 chromedriver）。

## 已知坑
- **一定要非 headless**：headless 模式更容易被 Cloudflare 判定為機器人，故意用有頭模式。
- 反偵測關鍵：`--disable-blink-features=AutomationControlled` + 隱藏 `navigator.webdriver` + 關閉 `enable-automation` 開關，缺一可能又被擋。
- 首頁熱身等待 8 秒、下載頁等待 8 秒、下載輪詢最多 40 秒——網路慢時可能要拉長，遇到 `NO FILE` 先檢查是不是被導到 Cloudflare 驗證頁（看 `current_url`／`title`）。

## 相關 Skill
- 抓到 PDF 後要萃取時程/金額 → 接 `extract_schedule_amount`（會直接吃快取）
