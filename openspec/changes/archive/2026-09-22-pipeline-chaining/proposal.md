## Why

`subsidy_crawler` 目前是三段獨立 CLI（`run.py` 爬蟲 → `extract_fields.py` 萃取 → `postprocess.py` 去重），彼此靠人工手動指定 CSV 檔名銜接，且下載到 `data/pdf_cache/` 的原始須知檔案沒有清除機制、會隨排程重複執行無限累積（已手動清過一次，省下 355MB）。最終目標是把整條管線變成「能固定排程、重複執行」的工具，這需要：① 快取有自我清理能力、② 階段之間有一份程式可直接消費的交接格式（而非仰賴人工挑檔名）、③ 有一支可一次執行到底的串接程式。本次不含「用什麼機制排程觸發」（Task Scheduler / n8n），留待下一輪決定。

## What Changes

- **pdf_cache 自動清除**：爬蟲階段（`run.py`）與萃取階段（`extract_fields.py`）下載成功並已把結果穩定寫入終點檔案後，預設自動刪除對應的原始快取檔；新增 `--keep-cache` CLI 旗標可關閉此行為。萃取階段僅對「成功」列清除，失敗列（下載失敗/抽字失敗/LLM失敗等）維持保留快取供重跑續用。
- **中間資料格式雙軌輸出**：爬蟲與萃取兩階段的既有 CSV 輸出邏輯與檔名不變（作為人工核對備份）；同步新增 JSON/JSONL 鏡像輸出。下一階段的讀取邏輯改為讀取上一階段的 JSON/JSONL（依副檔名自動判斷讀 CSV 或 JSON，向下相容既有的人工整理 CSV）。去重階段（`postprocess.py`）的最終覆蓋輸出同樣雙軌寫出 CSV＋JSONL。
- **新增串接程式** `subsidy_crawler/pipeline.py`：直接以函式呼叫依序執行爬蟲 → 萃取 → 去重三階段，提供 `python -m subsidy_crawler.pipeline` 一鍵跑完整條管線（可傳遞 `--keep-cache`）。**不含**排程觸發機制本身。

## Capabilities

### New Capabilities

- `subsidy-pipeline-chaining`：涵蓋「原始檔快取生命週期管理（自動清除＋保留例外＋可關閉旗標）」「跨階段 JSON/JSONL 資料交接契約（CSV 並存為人工備份）」「一鍵端到端管線執行」三組行為契約。

### Modified Capabilities

<!-- 無：既有 `subsidy-field-extraction` 能力（9 欄萃取邏輯本身）不變，本次只改其輸入/輸出的檔案格式與快取生命週期，不改萃取判斷邏輯。 -->

## Impact

- **既有檔案**：`subsidy_crawler/run.py`（新增 `keep_cache` 參數與 `--keep-cache` CLI）、`subsidy_crawler/common/store.py`（CSV 寫出同時新增 JSONL 鏡像）、`subsidy_crawler/extract_fields.py`（輸入依副檔名判斷讀法、輸出統一經 `_emit()` 同時寫 CSV+JSONL、新增 `keep_cache` 參數與 `--keep-cache` CLI）、`subsidy_crawler/postprocess.py`（輸入依副檔名判斷讀法、輸出新增 JSONL 鏡像）。
- **新增檔案**：`subsidy_crawler/pipeline.py`。
- **不影響**：各站 adapter 的抓取邏輯、LLM 9 欄萃取判斷邏輯（`common/llm.py`）、去重規則本身（`postprocess.py` 的比對演算法）皆不變；`data/pdf_cache/` 的下載/快取比對邏輯（`common/http.py`、`common/textio.py`、`common/render.py`）不變，只是多了下游的刪除呼叫。
- **依賴/環境**：無新增外部依賴，皆用標準庫 `json`。
