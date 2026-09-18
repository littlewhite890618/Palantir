## 1. pdf_cache 自動清除（爬蟲階段）

- [x] 1.1 `run.py`：`run_site()`／`run_all()` 新增 `keep_cache=False` 參數
- [x] 1.2 下載成功後（`http.download`／`render.selenium_download` 回傳 `path` 之後），非 `keep_cache` 時 `os.remove(path)`（try/except OSError，非致命）
- [x] 1.3 CLI `main()` 新增 `--keep-cache` 旗標，往下傳給 `run_site`/`run_all`
- [x] 1.4 驗證：`python -m subsidy_crawler.run --site kinmen` 執行後 `data/pdf_cache/` 無該次下載殘留；加 `--keep-cache` 再跑一次應保留

## 2. pdf_cache 自動清除（萃取階段）

- [x] 2.1 `extract_fields.py`：`run()` 新增 `keep_cache=False` 參數
- [x] 2.2 只在成功分支（`rec["萃取模型"] = model` 之後、寫列之後）刪除快取；下載失敗／抽字失敗／無文字層／LLM失敗四種分支維持保留快取
- [x] 2.3 CLI `main()` 新增 `--keep-cache` 旗標
- [x] 2.4 驗證：對含至少一筆會失敗連結的小量輸入執行，確認成功列快取被刪、失敗列快取仍在

## 3. 爬蟲輸出新增 JSONL 鏡像

- [x] 3.1 `common/store.py::save()`：寫 CSV 的同時，從同一份 `rows` 額外寫一份 JSONL（路徑＝CSV 路徑把副檔名換成 `.jsonl`，一行一筆）
- [x] 3.2 驗證：`notices.csv` 與 `notices.jsonl` 筆數與內容一致

## 4. 萃取階段輸入/輸出雙格式

- [x] 4.1 `run(in_path, ...)` 依副檔名自動判斷讀法：`.csv` 走現有 `csv.DictReader`，`.json`/`.jsonl` 走 JSON 讀取；確認 `dedup()` 對兩種來源的 `rows` 形狀處理一致
- [x] 4.2 新增 `_emit(rec)` helper：同時寫 CSV 一列與 JSONL 一行（各自 flush），取代現有 5 處 `writer.writerow(rec); fout.flush()`（下載失敗／抽字失敗／無文字／LLM失敗／成功）
- [x] 4.3 pdf_cache 清除（見 2.2）改掛在 `_emit()` 之後的成功分支
- [x] 4.4 驗證：`python -m subsidy_crawler.extract_fields --in data/notices.jsonl --limit 3` 執行後，`fields_extracted.csv` 與 `.jsonl` 筆數、欄位值一致，且含失敗列

## 5. 去重階段輸入/輸出雙格式

- [x] 5.1 `postprocess.py::run(in_path, ...)` 輸入依副檔名判斷讀 CSV 或 JSONL
- [x] 5.2 輸出維持現有「覆蓋寫回 CSV」行為不變，額外同步覆蓋寫一份同路徑的 `.jsonl`
- [x] 5.3 驗證：`python -m subsidy_crawler.postprocess --in data/fields_extracted.jsonl --dry-run` 統計輸出與改動前一致；正式執行後 CSV 與 JSONL 內容一致

## 6. 串接程式 `pipeline.py`

- [x] 6.1 新增 `subsidy_crawler/pipeline.py`：依序直接呼叫 `run.run_all()` → `extract_fields.run()` → `postprocess.run()`，中間路徑以上一階段實際輸出的 `.jsonl` 路徑自動接續，不需人工指定
- [x] 6.2 CLI 提供 `python -m subsidy_crawler.pipeline`，`--keep-cache` 旗標同時往爬蟲與萃取兩階段傳遞
- [x] 6.3 驗證：以小範圍設定（例如單一站點或 `--limit`）跑通端到端，確認最終 `fields_extracted.csv`/`.jsonl` 為去重後結果

## 7. 收尾與確認

- [x] 7.1 確認各站 adapter、`common/llm.py` 的 9 欄萃取判斷邏輯、`postprocess.py` 的去重比對演算法本身完全未被更動
- [x] 7.2 確認 CSV 輸出內容（欄位、順序、資料）與改動前逐位元組一致，避免既有人工核對流程被打斷
- [x] 7.3 `openspec validate --strict` 通過
- [x] 7.4 更新 `md/PROGRESS.md` 記錄本次改動（依既有慣例）
