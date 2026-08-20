# -*- coding: utf-8 -*-
"""
common/llm.py — 用 OpenRouter 免費模型把須知全文萃取成 9 個結構化欄位。

- 金鑰只從環境變數 OPENROUTER_API_KEY 讀，不落地成明碼。
- MODELS：免費模型清單（可抽換；免費名單會變動，跑前對 OpenRouter 現況確認）。
- 容錯：HTTP 429／非 200／JSON 解析失敗／輸出被截斷（finish_reason=length）／
  缺欄位 → 換清單下一個模型重試，輪替至成功或用盡。
- 申請機關「不」由 LLM 抽（見 extract_fields.py 的 deterministic 對映）。
"""
import os
import re
import json
import time
import requests

# 多供應商：各家用 OpenAI 相容的 chat/completions 端點，只差 base URL 與金鑰環境變數。
PROVIDERS = {
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "key_env": "GEMINI_API_KEY",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "key_env": "OPENROUTER_API_KEY",
    },
}

# (供應商, 模型)：主用 Gemini（免費額度大），OpenRouter 免費模型當備援 fallback。
# 要換模型只改這個清單，其餘程式不動；某供應商沒設金鑰會自動略過其模型。
MODELS = [
    ("gemini", "gemini-3.5-flash-lite"),                # 主：免費 RPD 500（3.6-flash 只有 20）
    ("gemini", "gemini-3.1-flash-lite"),                # Gemini 備：另一把 RPD 500
    ("openrouter", "z-ai/glm-5.2:free"),                # 最終備援
    ("openrouter", "nvidia/nemotron-3-super-120b-a12b:free"),
]

MAX_TOKENS = 16000     # 容納「完整照列」的長清單（原 8000 對長契約範本會截斷）
TIMEOUT = 240

# --- 節流 / 退避（避免瞬間打爆免費每分鐘額度）---
REQUEST_GAP = 4.0      # 請求間隔：每次呼叫前至少間隔幾秒（全域節流，事前預防）
MAX_429_RETRIES = 4    # 同一模型遇 429 的重試次數（事後補救）
BACKOFF_BASE = 5       # 退避基數：5→10→20→40 秒（指數，上限 BACKOFF_CAP）
BACKOFF_CAP = 75       # 上限拉到 75s（Gemini 免費 20/分，429 常要求等 ~54s）

_last_call = [0.0]     # 全域：上次送出請求的時間戳（跨 extract_9 呼叫共用）


def _throttle():
    """請求間隔：確保任兩次 API 呼叫至少間隔 REQUEST_GAP 秒。"""
    dt = time.time() - _last_call[0]
    if dt < REQUEST_GAP:
        time.sleep(REQUEST_GAP - dt)
    _last_call[0] = time.time()


def _retry_after(r, attempt):
    """退避秒數：優先照伺服器指定（Retry-After 標頭，或回應內文的『retry in Xs』），
    否則指數退避（上限 BACKOFF_CAP）。"""
    ra = r.headers.get("Retry-After")
    if ra:
        try:
            v = int(float(ra))
            if 0 < v <= 120:
                return v + 1
        except Exception:
            pass
    # Gemini/Google 的 429 常把秒數寫在內文：「Please retry in 54.11s」
    try:
        m = re.search(r"retry in\s*([\d.]+)s", r.text, re.I)
        if m:
            v = float(m.group(1))
            if 0 < v <= 120:
                return int(v) + 2      # 多等 2 秒保險
    except Exception:
        pass
    return min(BACKOFF_BASE * (2 ** attempt), BACKOFF_CAP)

# LLM 要回傳的 9 個欄位（申請機關由程式判定，不在此）
LLM_FIELDS = ["標題", "描述", "申請資格", "補助金額上限", "補助比例",
              "申請截止日期", "應備資料", "申請方式", "諮詢窗口"]

SYS_PROMPT = """你是政府補助「申請須知」的資訊萃取器。從須知全文抽出下列欄位，只輸出一個 JSON 物件，不要任何多餘文字或 markdown：
{
 "標題": 計畫正式名稱。移除年度(如「115年度」「115年」)、開頭流水序號(如「01-」)、以及「申請須知/須知」等字樣，只留計畫名,
 "描述": 計畫目的/緣起/說明的摘要(2~3句即可),
 "申請資格": 誰可以申請。完整照原文列出所有資格條件，不要摘要、不要省略,
 "補助金額上限": 最高補助金額。一律格式化為「N萬元」(阿拉伯數字或國字皆可辨識，換算成萬元；若有多個取最高)。找不到留空字串,
 "補助比例": 補助占總經費的百分比。只有在補助金額上限找不到時才填，否則留空字串,
 "申請截止日期": 收件/受理的截止日期。務必排除「計畫執行期程」「核定後X個月」這類期間。**若分多梯次/多批次收件，務必逐一列出「所有」梯次的截止日，絕對不可只取其中一梯**(例:第一梯 115/3/31；第二梯 115/6/1；第三梯 115/7/31；第四梯 115/10/30)；先掃過全文確認總共有幾梯再全部寫出。沒有明確截止日就留空字串,
 "應備資料": 申請時須檢附/繳交的文件清單。完整照原文逐項列出，不要摘要。以標題為『應備資料／應檢附文件／應備申請資料／申請應備資料』的那個正式章節為準；若文中另有「送件說明」所列的附件名稱及份數，那只是送件摘要，不得用它取代正式章節的內容。不要納入『提案計畫書格式/撰寫規定』等其他章節。務必逐字保留原文的分組標題(例如「申請階段」「審查階段」「【系統填寫】」「【自行上傳】」)，不得省略；並一併列出各附件名稱與編號,
 "申請方式": 如何提出申請(受理/送件方式與步驟)。只描述送件方式與步驟，不要把應備文件清單再抄一遍(文件清單放在「應備資料」欄即可),
 "諮詢窗口": 聯絡電話/信箱/承辦窗口
}
規則：任何欄位若文件中找不到，一律填空字串 ""，絕對不可臆測或杜撰。清單型欄位(申請資格/應備資料/申請方式)寧可完整照抄也不要精簡。所有值用繁體中文。"""

# 各機關家族的欄位標籤提示（來源＝使用者人工確認的 1–10 清單）。
_SBIR_HINT = ("描述看『計畫說明』；申請資格看『申請資格/計畫申請』；補助金額看『最高補助上限』；"
              "截止日看『受理期間/收件截止日期』；應備看『應備資料』。")
_DEPT_HINT = {
    "經濟部產業發展署": ("描述看『前言/說明/目的/計畫說明』；申請資格看『補助資格條件/申請資格/適用對象』；"
                   "補助金額(數字或國字)看『補助上限為/輔導款/政府款』；截止日看『計畫時程/受理期間/受理時間/收件日期認定/申請期限/申請作業』；"
                   "應備看『應備申請資料/應備資料/應備文件/申請資料』；申請方式看『申請方式/申請程序/受理方式』；諮詢看『諮詢專線/聯絡窗口』。"),
    "經濟部中小及新創企業署": ("描述看『緣起/計畫目的/計畫目標/依據』；申請資格看『申請資格』；"
                     "補助金額看『補助款額度/輔導經費/補助上限/補助金額』；截止日看『受理期間/計畫申請時間/申請與執行時間/收件截止日期/申請截止期限』；"
                     "應備看『申請文件/應備資料』；申請方式看『申請方式/申請說明』；諮詢看『諮詢窗口/諮詢服務/聯絡窗口』。"),
    "臺北市": ("描述看『目的』；申請資格看『符合下列條件者/申請資格/符合下列資格者』；補助金額看『每案補助/最高補助金額/補助類別與內容』；"
            "應備看『申請人應檢附下列文件各一份/申請應備文件』；申請方式看『申請程序』；諮詢看『服務窗口』。（截止日可能未明列，請從全文判斷）"),
    "經濟部產業技術司": ("描述在標題下一段或『說明』；申請資格看『申請資格』；補助金額看『補助款』；"
                  "截止日看『徵案期間/送件時程/受理至』；應備看『應備資料』；申請方式看『申請方式』；諮詢看『聯絡窗口/諮詢專線』。"),
    "數位發展部": ("描述看『計畫說明』；申請資格看『申請資格/參選資格』；截止日看『公告受理日期』；"
              "應備看『應備資料』；申請方式看『徵案方式/申請方式』；諮詢看『諮詢服務』。（補助金額可能未明列，請從全文判斷）"),
    "國際貿易署": ("描述看『目的』；申請資格看『申請資格』；補助金額看『補助上限/補助額度』；截止日看『受理期間』；"
              "應備看『申請應備資料』；申請方式看『辦理方式/申請方式』；諮詢看『服務窗口』。"),
    "經濟部商業發展署": ("描述看『依據/目的/目標』；申請資格看『申請資格/符合下列資格與條件』；"
                   "補助金額看『補助經費上限/輔導經費/輔導案/計畫經費』；截止日看『受理時間/申請期間/申請時間/申請期程/收件期間』；"
                   "應備看『應備文件/繳交文件/應備資料/申請文件』；申請方式看『申請方式/申請說明』；諮詢看『諮詢服務/聯絡窗口』。"),
    "原住民族委員會": ("描述看『目的』；申請資格看『申請資格』；補助金額看『補助額度/補助費用/每案補助款/補助經費』；"
                 "截止日看『收件期限/申請受理』；應備看『應備文件』；申請方式看『申請方式』。（諮詢窗口可能未明列，請從全文判斷）"),
}


def hint_for(department, is_sbir):
    """回傳該機關/計畫的欄位標籤提示；SBIR 一律用 SBIR 提示；未收錄者回空字串（LLM 裸抽）。"""
    if is_sbir:
        return _SBIR_HINT
    return _DEPT_HINT.get(department, "")


def _key(provider):
    """回傳該供應商的金鑰（環境變數）；沒設回 None（該供應商模型會被略過）。"""
    env = PROVIDERS[provider]["key_env"]
    return os.environ.get(env, "").strip() or None


def _parse_json(s):
    s = (s or "").strip()
    s = re.sub(r"^```(?:json)?", "", s).strip()
    s = re.sub(r"```$", "", s).strip()
    i, j = s.find("{"), s.rfind("}")
    if i >= 0 and j > i:
        s = s[i:j + 1]
    return json.loads(s)


def extract_9(text, department, filename, hint, models=None):
    """把須知全文抽成 9 欄 dict。回傳 (data, model_used, note)。
    失敗（所有模型都不成）回傳 (None, None, 錯誤摘要)。"""
    models = models or MODELS
    user = (f"機關：{department}\n檔名：{filename}\n欄位提示：{hint}\n\n"
            f"=== 須知全文 ===\n{text[:100000]}")
    attempts = []
    payload = {"temperature": 0, "max_tokens": MAX_TOKENS,
               "messages": [{"role": "system", "content": SYS_PROMPT},
                            {"role": "user", "content": user}]}
    for provider, model in models:
        tag = f"{provider}/{model}"
        key = _key(provider)
        if not key:                            # 該供應商沒設金鑰 → 略過其模型
            attempts.append(f"{tag}:無金鑰")
            continue
        url = PROVIDERS[provider]["url"]
        headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json"}
        # 收斂輪替：每個模型先「退避重試」把 429 等過去，真的不行才換下一個模型
        for attempt in range(MAX_429_RETRIES + 1):
            _throttle()                        # 請求間隔（事前預防）
            try:
                r = requests.post(url, headers=headers,
                                  json={"model": model, **payload}, timeout=TIMEOUT)
            except Exception as ex:
                attempts.append(f"{tag}:{type(ex).__name__}")
                break                          # 連線層錯誤 → 換模型
            # 暫時性錯誤（限流 429、過載 503/500/502/529）：退避重試「同一個」模型
            if r.status_code in (429, 500, 502, 503, 529):
                wait = _retry_after(r, attempt)
                attempts.append(f"{tag}:{r.status_code}→等{wait}s")
                if attempt < MAX_429_RETRIES:
                    time.sleep(wait)
                    continue                   # 重試同一模型（等它回血）
                break                          # 重試用盡 → 換下一模型
            if r.status_code != 200:
                attempts.append(f"{tag}:HTTP{r.status_code}:{r.text[:80]}")
                break                          # 其他（如 4xx）該模型無望 → 換模型
            try:
                choice = r.json()["choices"][0]
            except Exception:
                attempts.append(f"{tag}:回應異常")
                break
            if choice.get("finish_reason") == "length":
                attempts.append(f"{tag}:截斷")
                break                          # 這模型輸出過長 → 換模型
            try:
                data = _parse_json(choice["message"]["content"])
            except json.JSONDecodeError:
                attempts.append(f"{tag}:JSON解析失敗")
                break
            missing = [f for f in LLM_FIELDS if f not in data]
            if missing:
                attempts.append(f"{tag}:缺欄{','.join(missing)}")
                break
            data = {f: (str(data.get(f, "")).strip()) for f in LLM_FIELDS}
            return data, tag, " / ".join(attempts)
    return None, None, " / ".join(attempts)
