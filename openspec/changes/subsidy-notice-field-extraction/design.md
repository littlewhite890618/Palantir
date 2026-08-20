## Context

見 proposal.md（Why）。既有 `extract_schedule_amount`（skill script）已含成熟的文字層：
`session`/`download`/`extract_text`（pdf/docx/odt/zip、含 legacy SSL 修正與快取）/`normalize`（NFKC），
以及規則式 `find_money`/`find_time`。13 份樣本查核已確認：穩定欄位靠章節標題可規則抓，
難欄（金額、截止日）純規則近半假陽性。使用者已提供各機關的欄位關鍵字清單與 7 條判定備註，
並提供 `OPENROUTER_API_KEY`。約束：Windows console 為 cp950（中文輸出需包 utf-8）；輸出檔皆 utf-8-sig。

## Goals / Non-Goals

**Goals:**
- 以最小新增程式，把「語意萃取」放進管線，讓 9 欄（尤其難欄）達到可用品質。
- 重用既有文字層，不重造下載/抽字/正規化。
- 成本趨近零（OpenRouter `:free` 模型），並對免費額度限制具容錯。
- 先以最小雛形驗證可行性，再投資正式模組。

**Non-Goals:**
- 不做規則式章節切分（8 個語意欄全交 LLM）。
- 不改既有爬蟲 adapter、不改 `extract_schedule_amount`、不動 year_check。
- 不處理多梯次截止日期的最終呈現規則（先擱置、待樣本出現再議）。
- 行業類別欄不做（已移除）。

## Decisions

- **LLM 萃取 vs 純規則**：選 LLM。純規則對難欄有天花板（查核實證）；忠實把語意判斷程式化＝呼叫 LLM。
  規則 `find_money`/`find_time` 保留為**交叉檢查旗標**（非主抽取），值不一致時於備註標記供人工核。
- **OpenRouter 免費模型＋輪替 vs 付費/自架**：選 OpenRouter `:free`。~300 份一次性成本趨近零；
  免費模型有每分鐘/每日額度上限，故採「主模型＋備援清單」，撞 429／JSON 解析失敗即輪替下一個模型。
  模型清單設為 config 可抽換（免費名單會變動，跑前對 OpenRouter 現況確認）。資料為公開政府 PDF，
  免費層可能記錄輸入無隱私疑慮。
- **申請機關 deterministic vs LLM 抽取**：選 deterministic（見 spec「申請機關 deterministic 對映」）。
  查核證實地方版內文只有「目的事業主管機關」樣板，LLM 硬抽會錯；改由來源機關＋SBIR 判定固定產生。
  SBIR 判定＝檔名或計畫名含 `SBIR`／`地方產業創新研發推動`／`地方型`。
- **關鍵字清單的用途**：作為 prompt 內「各機關欄位常見標籤」的**提示**（非硬規則）；LLM 讀全文語意找，
  提示主要幫難欄消歧。空白欄（digiplus 金額、taipei 截止、原民會諮詢）與未提供的 ndc → 裸抽。
- **文字層落點**：把 `download`/`extract_text`/`normalize` 由 skill script 搬入 `common/textio.py`，
  供套件與 skill 共用（單純搬移、行為不變），避免跨 `.claude/skills` 匯入的脆弱路徑。
- **輸出獨立檔**：`data/fields_extracted.csv`，以連結去重（仿 `common/store.py`），不併回 year_check。
- **雛形先行**：步驟 0 於 scratchpad 寫丟棄式腳本抽 2–3 份驗證免費模型可行性，過關才寫正式模組。

## Risks / Trade-offs

- [免費模型 JSON 輸出不穩] → 要求純 JSON 輸出 + 解析失敗重試/換模型；temperature=0 降低漂移。
- [免費額度／可用性隨時變動] → 模型清單 config 化、輪替容錯；跑前確認現況清單。
- [LLM 非完全決定性] → temperature=0 + 嚴格 schema + 規則交叉檢查旗標；難欄仍以人工抽樣校準收斂。
- [截止日期難欄仍可能誤判] → prompt 明確「排除執行期程」；規則 `find_time` 交叉比對；樣本階段針對性補提示。
- [長文超出 context] → 過長截斷至模型 context 內（多數須知可全塞）；必要時分段（先不做）。
- [金鑰外洩] → 僅環境變數、不落地；transcript 已含金鑰，建議用畢 rotate。

## Migration Plan

- 純新增，無資料遷移。回滾＝移除新增檔與輸出 CSV，既有系統不受影響。
- 上線分兩步：步驟 0 雛形（scratchpad）→ 步驟 1 正式模組（先跑 13 份校準，再去重全量跑 newnotices3.csv）。

## Open Questions

- 多梯次收件截止日期的最終呈現（全部列出／取最早收件截止／分欄）——待樣本實際出現多梯次案例再與使用者定；
  不影響本次模組結構與 spec（屆時以既有「留空/備註」承接）。
