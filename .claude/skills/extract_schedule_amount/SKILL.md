---
name: extract_schedule_amount
description: 當要從政府「申請須知」PDF/DOCX/ODT/ZIP 檔萃取每個補助計畫的時程（申請/執行時間）與金額（補助上限）時使用。這是 gov_subsidy 專案的主引擎。
---

# extract_schedule_amount — 時程/金額萃取主引擎

## 用途
給一份「補助案清單」，下載每個計畫的申請須知檔案，自動抽出**時程**與**金額**，輸出成一份 CSV。

## 輸入
一份 CSV，欄位：`部門,檔案名稱,連結`。範例見 `gov_subsidy/SPEC.md` §2。
⚠️ 2026-07-23 起 `gov_subsidy/data/` 已被清空（舊的 stage2/3/4_input.csv 已刪），要重跑須先重建輸入清單。

## 執行
```bash
python scripts/extract_schedule_amount.py <輸入CSV> <輸出CSV>
```
下載會快取到 `gov_subsidy/data/pdf_cache/`（已刪除，重跑會重新下載全部檔案）。

## 輸出
主檔欄位：`部門,計畫名稱,原始檔名,檔案類型,下載狀態,萃取狀態,時程_命中關鍵字,時程_值,時程_型態,金額_命中關鍵字,金額_值,金額_型態,備註,連結`
另產生 `<輸出檔>_debug.csv`（時程/金額命中的上下文，供人工核對）。

## 核心邏輯速查（詳見 `gov_subsidy/SPEC.md`）
- **時程 6 型**：強型（隨到隨受理／年月日／年月／斜線日期）+ 弱型（期程長度／純年份）+ 期程限制語（不超過X年為原則）
- **金額 3 型**：萬元金額／百分比／元金額；全文掃描「上限語境」取最高
- **國字數字支援**：`cn2int()` 把「一百萬元」「不超過3年為原則」轉阿拉伯數字（SPEC.md §7）
- **`normalize()` 含 `unicodedata.normalize("NFKC")`**：修正 PDF 常見的 CJK 相容表意字（如 `不`=U+F967）與全形符號比對失敗問題——這是最容易忽略但影響最大的一個坑

## 已知坑（遇到抓不到值/亂碼時先查這些）
1. **看起來正常卻比對失敗** → 十之八九是 CJK 相容表意字，確認 `normalize()` 有 NFKC。
2. **中文檔名存不住** → 本環境 Write 工具對中文檔名會靜默失敗，所有輸出/輸入檔名一律用英文。
3. **console 印中文會報錯**（cp950）→ 一律寫檔 UTF-8-SIG，不要 print 中文。
4. **老政府站連不上** → 需要 `LegacyTLSAdapter`（SECLEVEL=1, CERT_NONE），程式內已內建。
5. **特殊站**：雲林 Cloudflare 擋爬蟲需搭配 `_yunlin.py`（Selenium 非 headless）；Google Drive 公開資料夾需搭配 `_gdrive.py` 列檔；部分失效 URL 修補邏輯在 `_update_s4_urls.py`。三者都在 `gov_subsidy/scripts/`。

## 相關 Skill
- 只想重跑先前漏抓的少數列 → 用 `rerun_missing_extraction`
- 想拿一份清單比對這份主檔裡有沒有 → 用 `compare_program_list`
