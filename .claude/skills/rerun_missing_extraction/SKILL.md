---
name: rerun_missing_extraction
description: 當只想針對「先前萃取漏抓」的少數列重新抽取時程/金額（而非整批重跑）時使用，適合人工核對後標記出漏抓狀態、要精準補值的場景。
---

# rerun_missing_extraction — 只重跑漏抓列

## 用途
`extract_schedule_amount` 整批跑完後，若人工核對發現某幾列其實有值但沒抓到（漏抓），
用這支腳本**只重跑那幾列**，不用整批重來（省時間，也不影響已經正確的列）。

## 現況（重要）
`gov_subsidy/scripts/rerun_missing.py` 目前的 `FLAG`／`OVERRIDE_MONEY` 是**針對 2026-07-20
那次「4種漏抓狀態、共68列」的一次性設定**（寫死行號→狀態的對照表），不是通用工具。
若要重跑一批新的漏抓列，需要：
1. 依新的漏抓列清單，改寫 `FLAG` 字典（`{來源CSV: {狀態代碼: [行號,...]}}`）
2. 若有「找不到明確標籤、需依指示定向抓某個關鍵字附近金額」的個案，比照 `OVERRIDE_MONEY` 的模式加規則

## 執行
```bash
python scripts/rerun_missing.py
```
輸出 `gov_subsidy/data/rerun_result.csv`：`來源檔,行號,備註狀態,狀態說明,部門,檔案名稱,時程_命中,時程_值,金額_命中,金額_值,時程脈絡,金額脈絡,是否補到,連結`

## 這次(2026-07-20)的結果可參考
- 4 種漏抓狀態（都有國字/只金額國字/漏金額/漏時程）共 68 列，最終補回 67/68
- 唯一沒補：某文件經人工確認**本來就沒有**金額/期程，非引擎問題
- 詳細決策過程見 `gov_subsidy/SPEC.md` §7

## 已知坑
- 跟 `extract_schedule_amount` 共用同一套 `normalize()`/`find_time()`/`find_money()`，NFKC、國字轉換、中文檔名等坑同樣適用（見該 skill 的 SKILL.md）
- 重跑一律 `weak_ok=True`（不受 `TIME_SUPPRESS_WEAK` 壓制），因為這些列已知有真實時程

## 相關 Skill
- 完整重跑整批 → 用 `extract_schedule_amount`
