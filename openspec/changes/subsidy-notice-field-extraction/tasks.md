## 1. 步驟 0：最小雛形探路（scratchpad，丟棄式）

- [x] 1.1 在 scratchpad 寫獨立小腳本，重用既有 `download`/`extract_text`/`normalize` 抽 2–3 份代表 PDF 文字
- [x] 1.2 串 OpenRouter（讀環境變數 `OPENROUTER_API_KEY`），帶 9 欄 JSON schema 的 prompt，temperature=0
- [x] 1.3 挑 3 份跨家族樣本：① 縣市 SBIR（高雄）② 中央（商發署 aoc）③ 有空白欄（數發部 digiplus 金額）
- [x] 1.4 印出抽出的 9 欄，人工判定免費模型可行性（結果見 scratchpad/spike_result.md）
- [x] 1.5 【驗收關卡】結論：**品質可行**（9 欄正確、SBIR→中企署對映正確、空白欄裸抽成功、金額上限優先、截止日正確）。瓶頸為**免費模型速度慢(42~187s/份)且不穩(glm 3份掛2份，靠輪替救回)**＋金額格式不一致。→ 進步驟 2，但全量前建議評估改用便宜付費模型 + JSON 強制輸出

## 2. 步驟 1：文字層落地（common/textio.py）

- [x] 2.1 將 `session`/`download`/`extract_text`/`normalize` 由 `extract_schedule_amount.py` 搬入 `subsidy_crawler/common/textio.py`（逐字搬移、行為不變）
- [x] 2.2 驗證：模組可匯入、快取/SSL/zip 中文檔名邏輯原樣保留（表格處理照原定用 pdfplumber，PyMuPDF 並用經實測不穩定不採用）

## 3. OpenRouter 客戶端（common/llm.py）

- [x] 3.1 實作 `llm.py`：讀 `OPENROUTER_API_KEY`、POST chat/completions；`MODELS` 免費模型清單（config 可抽換）
- [x] 3.2 `extract_9(text, department, filename, hint)`：帶嚴格 9 欄 JSON schema 的 v3 prompt，temperature=0、max_tokens=8000
- [x] 3.3 容錯：HTTP 非200／截斷(finish_reason=length)／JSON 解析失敗／缺欄 → 換下一個模型重試，輪替至成功或用盡
- [x] 3.4 金鑰只走環境變數、不寫入任何檔（`_key()` 從 env 讀，缺則報錯）

## 4. 申請機關對映與 prompt 規則

- [x] 4.1 `agency_of()` deterministic 對映：SBIR→經濟部中小及新創企業署；非SBIR縣市→縣市政府；國際貿易署→經濟部國際貿易署；其餘中央照 DEPARTMENT
- [x] 4.2 `is_sbir()`：檔名或 LLM 標題含 SBIR／地方產業創新研發推動／地方型（台中/基隆檔名無SBIR字，靠 LLM 標題判定）
- [x] 4.3 prompt 納入各機關欄位關鍵字提示（`hint_for`，使用者 1–10 清單）＋v3 判定規則（標題去年度/去須知、金額上限優先、多梯次全列、截止日排除執行期程、清單完整照列、抽不到留空）

## 5. 主流程（extract_fields.py）

- [x] 5.1 讀輸入 CSV（欄位 部門/檔案名稱/連結，同既有引擎契約）
- [x] 5.2 去重：同 URL 去重；同計畫多格式擇一（`_title_key` 去格式標記 + `_prefer_pdf`）。實測 255→182 列
- [x] 5.3 對每筆：download → extract_text → normalize → `llm.extract_9`
- [x] 5.4 申請機關以 4.1 規則覆寫；`find_money`/`find_time` 最佳努力寫入「規則交叉檢查」欄（值不一致才標）
- [x] 5.5 寫獨立 `data/fields_extracted.csv`（utf-8-sig，以連結去重、可重跑跳過），15 欄；不動 year_check

## 6. 樣本校準（13 份 + Gemini 3/11 份）

- [x] 6.1 對 13 份代表樣本執行（sample13）＋後續用 Gemini 對 3/11 份重測
- [x] 6.2 人工核對 9 欄值 vs 原文脈絡（使用者逐份比對難欄）
- [x] 6.3 「先跑再針對性補」：① 清單型過簡→完整照列 ② 金額格式統一「N萬元」 ③ 多梯次截止日只取一梯→全部列出 ④ 應備資料多抓/漏分組標題→修法A ⑤ 應備資料章節標題變體(應備資料/應檢附文件/應備申請資料/申請應備資料)。**eii/產發署契約範本「應備資料挑錯章節」列為已知難處（Lite 兩次修 prompt 仍挑到送件說明清單，待人工複核）**

## 7. 全量與收尾

- [x] 7.1 對 `newnotices3.csv`（去重 182）全量跑，輸出 `data/fields_extracted.csv`。**成功 180/182**（剩桃園舊.doc、彰化連結失效）
- [x] 7.2 確認 year_check 及其他現有檔未被更動；產出無明碼金鑰（金鑰只走 env）
- [ ] 7.3 `requirements.txt`／README 補上新流程說明與 `GEMINI_API_KEY`／`OPENROUTER_API_KEY` 前提
- [x] 7.4 多梯次截止日案例（aoc 商發署整合型 4 梯）→ 已定「全部列出」並修 prompt 驗證通過

## 8. 模型策略與韌性（實測後追加，2026-08-19）

- [x] 8.1 llm.py 改**多供應商**：Gemini（OpenAI 相容端點）主 + OpenRouter 備援；`(provider, model)` 清單、缺金鑰自動略過
- [x] 8.2 免費額度實測：`gemini-3.6-flash` RPD 僅 20 不可用 → 改主 `gemini-3.5-flash-lite`＋備 `gemini-3.1-flash-lite`（RPD 各 500）
- [x] 8.3 節流+退避重試：REQUEST_GAP 間隔、429/503/5xx 退避（讀 Retry-After／內文「retry in Xs」）、收斂輪替、max_tokens 16k
- [x] 8.4 resume 修正：`load_done` 只跳過「成功」列 → 失敗會續傳重試（避免失敗列被當已完成）
- [x] 8.5 下載層失敗補救（寫進程式，非 skill）：`extract_docx` 改讀 `<w:tc>` 繞過合併儲存格 ValueError（補回產發署）；`download_via_browser` 遇 403 自動 Selenium 繞 Cloudflare（補回雲林）
- [x] 8.6 桃園已補：捨棄舊 .doc 連結，改用新來源 `invest.tycg.gov.tw/cp.aspx?n=848` 的當年度 PDF（外科手術式補該列）。剩彰化（getFile 連結失效需重找）
- [x] 8.7 交付：CSV `data/fields_extracted.csv` + 可搜尋網頁（Artifact）

## 9. 後處理：篩選＋去重（common → `postprocess.py`，2026-08-20）

- [x] 9.1 新增 `subsidy_crawler/postprocess.py`：讀 `fields_extracted.csv` → 篩選＋去重 → 覆蓋同檔；核心純函式 `filter_and_dedup`；`--dry-run`、`--drop-empty` 旗標
- [x] 9.2 篩選（金額上限＋截止皆空→移除）改為 `--drop-empty` 選項、**預設關閉、全數保留**（使用者定案）
- [x] 9.3 類型A 正規化（比對前）：標題去空白/分隔標點、截止日解析成標準日期（吸收機械差異，修好南投/卓越經營/跨域研發）
- [x] 9.4 去重規則 1–4（限同部門）：1 多格式擇一優先pdf；2 標題+金額+資格同隨機留一；3 標題+金額同留截止較晚(多梯次取最晚日)；4 標題同留三欄文字最長
- [x] 9.5 規則5（類型B）：同部門+金額相同+標題有包含關係+應備相似度≥0.75(退資格≥0.85)→併同計畫不同標題。防呆：金額相同排除子軌道(多店/單店)、標題包含排除姊妹子案(服務類vs產品類)
- [x] 9.6 規則5 加「申請類別守門」：兩筆來源檔名(讀 newnotices3.csv)帶互斥標記 `個別/共同/聯盟、單店/多店、產品類/服務類、初階/進階` 就不併（解臺南個別申請 vs 共同研發須知雷同誤併）
- [x] 9.7 檔案類型還原：用 `md5(連結)[:8]` glob pdf_cache 取副檔名（CSV 無此欄）；「隨機」用群組鍵當固定 seed 可重現；失敗列不參與、原樣保留
- [x] 9.8 全量：萃取181 → 去重後 156（155成功+1失敗）；備份 `data/fields_raw181.csv`（去重前完整181）；三網頁（原始182/去重156/被移除26）
- [ ] 9.9 擱置（類型C）：AI中央廚房 2000萬vs3000萬＝同計畫金額抽到別欄（萃取準度）→ 待人工複核；規則5 門檻已擋掉不誤併
