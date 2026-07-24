---
name: compare_program_list
description: 當要拿一份補助計畫清單（計畫名稱+機關）去比對是否已經在萃取主檔（時程金額萃取結果）裡、找出哪些不在時使用。
---

# compare_program_list — 清單模糊比對

## 用途
使用者常會另外拿到一份補助計畫清單（例如手動蒐集的~80筆），想知道**哪幾筆不在**
`extract_schedule_amount` 產出的主檔裡。因為兩邊的計畫名稱寫法常不一致（PDF標題 vs 描述性名稱），
用字元 bigram + Jaccard 相似度做模糊比對，而非精確字串比對。

## 輸入
- `data/compare_list.csv`：欄位 `序號,計畫名稱,機關`（待比對清單）
- `data/時程金額萃取結果.csv`：萃取主檔（中文檔名，⚠️ 本環境存不住、目前已遺失，需先由
  `extract_schedule_amount` 重新產出，且**建議改用英文檔名**再修改本腳本內的路徑）

## 執行
```bash
python scripts/compare_list.py
```
輸出 `data/compare_result.csv`：`序號,計畫名稱,機關,狀態,相似度,最相近master計畫,master部門`
狀態分三桶：`命中(在master)` / `疑似待確認` / `不在master`（相似度門檻 0.5 / 0.3，可調）。

## 比對規則（已定案，見對話歷史）
- 只看計畫本身，不管機關名稱是否一致（同一計畫可能被不同機關標示）
- 相似但不確定的列入「疑似待確認」，附上 master 最相近那筆讓人核對，不要自動判定
- SBIR 類計畫額外用「城市名+SBIR/地方型」規則輔助比對（見程式內 `city_sbir_in_master`）

## 已知坑
- `norm()` 函式會過濾常見尾綴（申請須知/補助計畫等）與年度字樣，比對前務必經過這層正規化
- 過短或以 `aoc` 開頭的候選名稱會被過濾（避免通用詞誤判）

## 相關 Skill
- 主檔不存在或要重新產生 → 先用 `extract_schedule_amount`
