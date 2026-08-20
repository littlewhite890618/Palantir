## Why

爬蟲已能收齊各機關「申請須知」連結，但下游只有 `extract_schedule_amount` 抽「時程＋金額」2 欄、且是純規則（關鍵字錨點＋視窗＋正則），無法產出可用的結構化補助資料。經 13 份代表樣本查核：穩定欄位靠章節標題可規則抓取，但難欄（補助金額、申請截止日期）純規則有近半假陽性、申請機關硬抽會抓到「目的事業主管機關」樣板。需要一個能理解語意的萃取能力，把每份須知轉成 9 欄結構化資料。

## What Changes

- 新增「補助須知欄位萃取」能力：從 PDF/DOCX/ODT/ZIP 須知抽出 **9 欄**（標題＝計畫名、描述、申請機關、申請資格、補助金額上限、補助比例、申請截止日期、應備資料、申請方式、諮詢窗口），一份文件輸出一列。
- 萃取採 **LLM（OpenRouter 免費模型＋輪替）** 做 8 個語意欄；**申請機關由程式 deterministic 對映**（SBIR→經濟部中小及新創企業署；非 SBIR 縣市→縣市政府；國際貿易署補「經濟部」；其餘中央照 DEPARTMENT）。
- 補助金額拆兩欄：**優先** `補助金額上限`（萬元，數字或國字，取最高），找不到才填 `補助比例`（總經費 X%）。
- 輸出**獨立** CSV `subsidy_crawler/data/fields_extracted.csv`，以連結去重、**不併回 year_check、不動任何現有檔**。
- 重用既有文字層（`download`/`extract_text`/`normalize`），`find_money`/`find_time` 降級為交叉檢查旗標。
- 導入新依賴：呼叫 OpenRouter HTTP API（金鑰走環境變數 `OPENROUTER_API_KEY`，不落地）。

## Capabilities

### New Capabilities

- `subsidy-field-extraction`: 從單份申請須知文件萃取 9 個結構化補助欄位並輸出為獨立 CSV 的能力，含申請機關 deterministic 對映、補助金額上限優先於比例、多格式去重、LLM 抽不到一律留空不杜撰等行為契約。

### Modified Capabilities

<!-- 無：既有 extract_schedule_amount（時程/金額）行為契約不變，本次為新增獨立能力。 -->

## Impact

- **新增檔**：`subsidy_crawler/common/textio.py`（由既有引擎搬入文字層）、`subsidy_crawler/common/llm.py`（OpenRouter 客戶端＋模型輪替）、`subsidy_crawler/extract_fields.py`（主流程）。
- **新增輸出**：`subsidy_crawler/data/fields_extracted.csv`（獨立，不影響 year_check）。
- **依賴/環境**：新增對 `openrouter.ai` 的網路呼叫；需 `OPENROUTER_API_KEY` 環境變數；`requirements.txt` 可能新增 HTTP 需求（沿用既有 `requests`）。
- **不影響**：既有爬蟲 adapter、`extract_schedule_amount`、`year_check.csv` 及其他資料檔皆不變。
