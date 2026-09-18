## Context

見 proposal.md（Why）。三段程式與相關檔案現況：

- `common/store.py::save()` 已把爬蟲抓到的列組成 `{連結: 整列dict}` 後整份重寫 CSV（`notices.csv`，欄位 部門/檔案名稱/連結/抓取時間）。
- `extract_fields.py::run()` 讀輸入 CSV（`csv.DictReader`，只用 部門/檔案名稱/連結 三欄）、逐筆處理，5 處各自呼叫 `writer.writerow(rec); fout.flush()`（下載失敗/抽字失敗/無文字/LLM失敗/成功），靠逐列 flush 達成崩潰安全的續傳（`load_done()` 只把「有萃取模型」視為成功、其餘會重試）。
- `postprocess.py::run(in_csv, out_csv, dry_run, drop_empty)` 一次性讀入全部列（`csv.DictReader`）、跨列比對去重、整份覆蓋輸出，介面已是乾淨的函式（非僅 CLI），可直接被其他程式呼叫。
- 快取（`data/pdf_cache/`）由三個地方共用同一套 `md5(url)[:8]` 雜湊當快取比對鍵：`common/http.py`（爬蟲階段一般下載）、`common/render.py::selenium_download`（爬蟲階段瀏覽器下載）、`common/textio.py::download`（萃取階段下載，含 403 時的瀏覽器備援）。三者的下載函式都直接回傳本地檔案路徑，可直接 `os.remove()`。

## Goals / Non-Goals

**Goals:**
- 讓 `pdf_cache` 在正常運作下不會無限累積，同時不犧牲既有「中途失敗可續傳」的安全性。
- 讓三階段之間有一份程式可直接消費、不需人工介入指定檔名的交接格式。
- 提供一個能被未來排程機制直接呼叫的單一進入點。

**Non-Goals:**
- 不決定排程觸發機制（Task Scheduler vs n8n）——那是下一輪的獨立決定。
- 不改變任何一站 adapter 的抓取邏輯、LLM 9 欄萃取的判斷邏輯、去重比對演算法本身。
- 不引入資料庫；JSON/JSONL 僅是檔案層級的交接格式，不是最終資料庫欄位設計。
- 不處理 `pdf_cache` 長期以外的保留策略（例如「失敗列快取要保留多久」的過期機制）——目前設計是失敗列永久保留直到成功或使用者手動清除。

## Decisions

- **快取清除時機＝該階段「已把結果寫進終點檔案」之後**，而非下載當下。理由：快取真正的用途是保護處理過程（中途崩潰可續傳），只要結果已經穩定落地，快取的任務就完成了。爬蟲階段的「終點」是 `notices` 已記入清單／已呼叫 `store.save()`；萃取階段的「終點」是該列已成功寫入 CSV/JSONL（有萃取模型值）。
- **只在成功分支清除，失敗分支保留**：直接沿用 `extract_fields.py` 既有的 `load_done()` 語意（「有萃取模型才算完成」），不需要新增額外的狀態欄位或旗標去追蹤「這個快取還需不需要」——用「該列有沒有寫出萃取模型」這個既有欄位本身當判斷依據。
- **`--keep-cache` 為單一全域旗標、非精細規則**：只分「清」與「不清」兩態，不做「保留 N 天」之類的過期策略（見 Non-Goals）。理由：使用情境主要是「正式排程跑（清）」vs「手動除錯需要核對原始檔（不清）」，兩態已足夠覆蓋目前需求，過度設計會增加不必要的複雜度。
- **JSON 角色＝下一階段的實際輸入，CSV 角色＝人工核對備份**（非兩者擇一）：CSV 的既有讀寫邏輯完全不動（風險最低、不影響任何手動校準流程），新增的 JSON/JSONL 寫出邏輯掛在既有寫檔的呼叫點旁邊。下一階段的讀取邏輯改成優先支援 JSON，但仍相容讀 CSV（見下一點），因此不是破壞性變更。
- **JSON 讀取用「副檔名判斷格式」而非新增獨立旗標**：`.csv` 走既有 `csv.DictReader`、`.json`/`.jsonl` 走 JSON 讀取，兩者讀出來的列形狀相同（`{部門,檔案名稱,連結}` 或萃取階段的 15 欄 dict），下游的 `dedup()`／比對邏輯不需要感知輸入格式。這讓既有「人工整理一份 CSV 再手動指定 `--in`」的校準工作流程完全不受影響。
- **萃取階段輸出改用共用 `_emit(rec)` helper 同時寫 CSV 列與 JSONL 行**：取代現有 5 處重複的 `writer.writerow(rec); fout.flush()`。JSONL 沿用「一行一筆、每筆寫完立刻 flush」以維持原本的崩潰安全特性；失敗列也要寫入 JSONL（`postprocess.py` 需要完整資料含失敗列才能正確統計「失敗列原樣保留」）。
- **`postprocess.py` 與 `store.py` 的 JSON 輸出不需要逐筆 flush 的 append 安全性**：兩者本來就是「算完一次性整份覆寫」，因此 JSON 部分直接在整份 CSV 寫完後，用同一份記憶體中的資料另外寫一份 JSONL 即可，不需要複製萃取階段的逐筆 flush 機制。
- **`pipeline.py` 用直接函式呼叫（import）而非 subprocess 呼叫既有 CLI**：三段程式的核心邏輯本來就已经是可呼叫的函式（`run.run_all()`、`extract_fields.run()`、`postprocess.run()`），直接 import 呼叫可拿到明確的回傳值/例外，不用處理 subprocess 的編碼、exit code、跨程序參數傳遞等額外複雜度。

## Risks / Trade-offs

- [快取清除後若要重新萃取歷史須知，原始檔可能已從政府網站下架，屆時無法重跑] → 使用者已知並接受此取捨（見 proposal 範圍），不在本次處理；未來如需要，可另外設計「成功列也保留一份長期封存」的機制。
- [`_emit()` 改動萃取階段既有的 5 處寫檔呼叫點，屬於既有穩定程式的重構] → 改動範圍集中在單一函式內、行為以「新增 JSONL 副作用」為主，CSV 那一半邏輯逐字保留不變；實作後以既有的 `--limit 3` 小量跑法驗證 CSV 內容與改動前一致。
- [三階段從獨立 CLI 變成可被 `pipeline.py` 直接 import 呼叫，`run.py`/`extract_fields.py`/`postprocess.py` 各自的 `if __name__ == "__main__":` 進入點須確認不會在被 import 時意外執行] → 三者現況的 CLI 邏輯已包在 `main()` 內、僅在 `__main__` 才呼叫，直接 import 呼叫其 `run()`/`run_all()` 是安全的，不需額外改動。

## Migration Plan

純新增行為＋既有輸出格式擴充（CSV 不變、多寫一份 JSON），無資料遷移、無破壞性變更。回滾＝移除 `pipeline.py`、移除三個既有檔案裡新增的 JSON 寫出與快取清除程式碼片段，CSV 相關邏輯本來就沒被動過。建議實作順序：先做 A（pdf_cache 清除，範圍最小、風險最低）→ 再做 B（JSON 雙軌輸出，逐檔案驗證 CSV 內容不變）→ 最後做 C（`pipeline.py`，依賴 A、B 都完成後才能串出正確的 JSON 交接）。
