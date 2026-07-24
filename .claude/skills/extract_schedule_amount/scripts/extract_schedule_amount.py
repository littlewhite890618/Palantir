# -*- coding: utf-8 -*-
"""
從申請須知檔案(PDF/DOCX/ODT)萃取「時程」與「金額」。
用法: python extract_schedule_amount.py 輸入CSV 輸出CSV
輸入CSV欄位: 部門,檔案名稱,連結
輸出CSV欄位: 部門,計畫名稱(PDF標題),原始檔名,檔案類型,下載狀態,萃取狀態,
             時程_命中關鍵字,時程_值,時程_型態,金額_命中關鍵字,金額_值,金額_型態,備註
所有輸出寫檔(utf-8-sig),不在console印中文(避免cp950錯誤)。
下載會快取到 gov_subsidy/data/pdf_cache/ ,已存在則跳過。
"""
import sys, os, re, csv, io, ssl, hashlib, urllib.parse, zipfile, unicodedata
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

requests.packages.urllib3.disable_warnings()

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "..", "data", "pdf_cache")
os.makedirs(CACHE, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Accept": "*/*",
}

class LegacyTLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *a, **k):
        ctx = create_urllib3_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        k["ssl_context"] = ctx
        return super().init_poolmanager(*a, **k)

def session():
    s = requests.Session()
    s.headers.update(HEADERS)
    s.mount("https://", LegacyTLSAdapter())
    return s

# ---------- 下載 ----------
def safe_name(dep, name, url):
    base = re.sub(r'[\\/:*?"<>|]+', "_", (dep + "_" + (name or ""))[:60])
    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    return f"{base}_{h}"

def detect_ext(content, ctype, url):
    if content[:4] == b"%PDF" or b"%PDF" in content[:2048]:
        return "pdf"
    if content[:2] == b"PK":  # zip-based: docx/odt/xlsx/zip
        try:
            z = zipfile.ZipFile(io.BytesIO(content))
            names = z.namelist()
            if "word/document.xml" in names:
                return "docx"
            if "content.xml" in names and any("opendocument" in n or n == "mimetype" for n in names):
                mt = z.read("mimetype").decode("ascii", "ignore") if "mimetype" in names else ""
                if "text" in mt:
                    return "odt"
                return "odt" if "content.xml" in names else "zip"
            return "zip"
        except Exception:
            return "zip"
    low = url.lower()
    for e in ("pdf", "docx", "odt", "zip"):
        if low.split("?")[0].endswith("." + e):
            return e
    if ctype and "pdf" in ctype:
        return "pdf"
    return "unknown"

def download(sess, url, dep, name):
    """回傳 (path, ext, status)"""
    url = url.strip()
    # 去除 chrome-extension:// 前綴,取最後一個真實 https 網址
    if 'chrome-extension' in url and 'https://' in url:
        url = 'https://' + url.split('https://')[-1]
    else:
        m = re.search(r'https?://.*', url)
        if m:
            url = m.group(0)
    stem = safe_name(dep, name, url)
    # 檢查快取
    for f in os.listdir(CACHE):
        if f.startswith(stem + "."):
            p = os.path.join(CACHE, f)
            return p, f.rsplit(".", 1)[1], "快取"
    try:
        r = sess.get(url, timeout=60, verify=False, allow_redirects=True)
        if r.status_code != 200:
            return None, None, f"HTTP{r.status_code}"
        content = r.content
        ext = detect_ext(content, r.headers.get("Content-Type", ""), url)
        if ext in ("unknown",):
            return None, None, "非檔案(可能是網頁)"
        p = os.path.join(CACHE, stem + "." + ext)
        with open(p, "wb") as fh:
            fh.write(content)
        return p, ext, "成功"
    except Exception as e:
        return None, None, "下載錯誤:" + type(e).__name__

# ---------- 抽文字 ----------
def extract_pdf(path):
    import pdfplumber
    parts, title = [], ""
    with pdfplumber.open(path) as pdf:
        try:
            title = (pdf.metadata or {}).get("Title", "") or ""
        except Exception:
            title = ""
        for pg in pdf.pages:
            t = pg.extract_text() or ""
            parts.append(t)
            for tb in (pg.extract_tables() or []):
                for row in tb:
                    parts.append(" ".join(c or "" for c in row))
    return "\n".join(parts), title.strip()

def extract_docx(path):
    from docx import Document
    d = Document(path)
    parts = [p.text for p in d.paragraphs]
    for tb in d.tables:
        for row in tb.rows:
            parts.append(" ".join(c.text for c in row.cells))
    core = d.core_properties
    return "\n".join(parts), (core.title or "").strip()

def extract_odt(path):
    from odf.opendocument import load
    from odf import text as odftext, teletype
    doc = load(path)
    parts = []
    for el in doc.getElementsByType(odftext.P):
        parts.append(teletype.extractText(el))
    for el in doc.getElementsByType(odftext.H):
        parts.append(teletype.extractText(el))
    return "\n".join(parts), ""

def _zip_realname(nm):
    # zip 內中文檔名編碼修正(cp437 -> big5/utf-8)
    for enc in ("big5", "utf-8"):
        try:
            return nm.encode("cp437").decode(enc)
        except Exception:
            pass
    return nm

def extract_zip(path):
    z = zipfile.ZipFile(path)
    cands = [i for i in z.infolist()
             if i.filename.lower().endswith((".pdf", ".docx", ".odt"))]
    # 優先檔名含「申請須知」
    cands.sort(key=lambda i: 0 if "須知" in _zip_realname(i.filename) else 1)
    for info in cands:
        low = info.filename.lower()
        ext = "pdf" if low.endswith(".pdf") else ("docx" if low.endswith(".docx") else "odt")
        tmp = path + ".inner." + ext
        with open(tmp, "wb") as fh:
            fh.write(z.read(info))
        try:
            txt, title = extract_text(tmp, ext)
        except Exception:
            txt, title = "", ""
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass
        if "申請須知" in txt or "須知" in _zip_realname(info.filename):
            return txt, (title or _zip_realname(info.filename))
    return "", ""

def extract_text(path, ext):
    if ext == "pdf":
        return extract_pdf(path)
    if ext == "docx":
        return extract_docx(path)
    if ext == "odt":
        return extract_odt(path)
    if ext == "zip":
        return extract_zip(path)
    return "", ""

# ---------- 正規化 & 關鍵字定位 ----------
def normalize(s):
    # NFKC:相容表意字(U+F900-FAFF,如 不=U+F967)→標準字、全形→半形、％→%
    s = unicodedata.normalize("NFKC", s)
    # 全形數字/符號轉半形(NFKC 後多為冗餘,保留作保險)
    out = []
    for ch in s:
        o = ord(ch)
        if 0xFF10 <= o <= 0xFF19:      # 全形0-9
            out.append(chr(o - 0xFEE0))
        elif o == 0x3000:              # 全形空白
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)

# ---------- 國字數字 ----------
_CN = {'零': 0, '〇': 0, '一': 1, '二': 2, '兩': 2, '三': 3, '四': 4, '五': 5,
       '六': 6, '七': 7, '八': 8, '九': 9,
       '壹': 1, '貳': 2, '參': 3, '叁': 3, '肆': 4, '伍': 5, '陸': 6, '柒': 7, '捌': 8, '玖': 9}
_CNU = {'十': 10, '拾': 10, '百': 100, '佰': 100, '千': 1000, '仟': 1000}
_CNB = {'萬': 10000, '万': 10000, '億': 100000000}
CN_CHARS = '零〇一二兩三四五六七八九十百千萬万億壹貳參叁肆伍陸柒捌玖拾佰仟'
_CNY = '零〇一二兩三四五六七八九十'   # 年/月用的國字(不含萬/億)

def cn2int(s):
    """國字數字字串 → 整數(支援一般國字與公文大寫)。"""
    total = sec = num = 0
    for ch in s:
        if ch in _CN:
            num = _CN[ch]
        elif ch in _CNU:
            sec += (num or 1) * _CNU[ch]
            num = 0
        elif ch in _CNB:
            total += (sec + num) * _CNB[ch]
            sec = num = 0
    return total + sec + num

def _has_cn(s):
    return any(c in CN_CHARS for c in s)

def to_wan(s):
    """『萬元』前的數字部分(阿拉伯或國字)→ 以『萬』為單位的整數;無法解析回 None。"""
    s = (s or "").strip().strip("，、 ")
    if _has_cn(s):
        v = cn2int(s)
        return v if v > 0 else None
    d = s.replace(",", "")
    return int(d) if d.isdigit() else None

def cn_num_to_ar(s):
    """把字串裡緊貼 年/個月/月 的國字數字轉成阿拉伯(其餘不動)。"""
    return re.sub('[' + _CNY + '百千]+(?=年|個月|月)', lambda m: str(cn2int(m.group(0))), s)

def norm_pct(s):
    """百分比字串正規化為『N%』。"""
    s = s.strip()
    m = re.search(r'百分之\s*([' + _CNY + r'百]+|\d+)', s)
    if m:
        g = m.group(1)
        return (str(cn2int(g)) if _has_cn(g) else g) + '%'
    m = re.match(r'(\d)\s*成$', s)
    if m:
        return str(int(m.group(1)) * 10) + '%'
    return re.sub(r'\s+', '', s)

# 錨點依「排程可靠度」排序;執行期間最後(常出現在契約條款被誤抓)
TIME_ANCHORS = ["公告受理日期", "收件截止日期", "收件期間", "收件日期",
                "收件地點及截止日期", "收件", "服務窗口", "申請期間", "受理期間",
                "計畫申請時間", "申請時間", "受理至", "計畫期程", "執行期程",
                "本期執行時間", "執行期間"]
MONEY_ANCHORS = ["補助金額上限", "補助上限", "補助額度", "補助經費", "輔導經費", "申請額度"]

# 這些來源是契約範本,內文duration全是條款boilerplate → 時程只採日期,不採期程長度
TIME_SUPPRESS_WEAK = {"經濟部產業發展署", "經濟部產業技術司"}

# 強型(日期/隨到隨)先試,弱型(期程長度/純年份)後試
TIME_STRONG = [
    ("隨到隨受理", r'隨到隨(?:受理|審查|審|辦理)|即日起(?:至|受理|辦理)?|額滿為止|隨收隨審'),
    ("年月日", r'(?:民國)?1?\d{2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日'
               r'(?:\s*(?:起|迄|至|~|～|－|—|-|到)\s*(?:民國)?(?:1?\d{2}\s*年)?\s*\d{1,2}\s*月\s*\d{1,2}\s*日)?'),
    ("年月", r'1?\d{2}\s*年\s*\d{1,2}\s*月(?:\s*(?:起|迄|至|~|～|-|到)\s*(?:1?\d{2}\s*年)?\s*\d{1,2}\s*月)?'),
    ("日期(斜線)", r'\d{2,3}[./]\d{1,2}[./]\d{1,2}'
                 r'(?:\s*(?:起|至|~|～|-|到)\s*(?:\d{2,3}[./])?\d{1,2}[./]\d{1,2})?'),
]
TIME_WEAK = [
    ("期程長度", r'(?<![\d.])\d{1,2}\s*個月(?!\s*內)|(?<![\d.])[1-9]\s*年(?!\s*度)(?!\s*\d{1,2}\s*月)(?!\s*內)'
                 r'|[一二兩三四五六七八九十]+\s*個月(?!\s*內)'
                 r'|[一二兩三四五六七八九十]+\s*年(?:\s*(?:又|零)?\s*[一二兩三四五六七八九十]+\s*個?月)?(?!\s*度)(?!\s*內)'),
    ("純年份", r'1[01]\d\s*年度?'),
]
# 明確期程限制語(不超過X年/以X年為原則/最長X年);此語境為真時程,不受 weak 壓制
DUR_LIMIT = re.compile(
    r'(?:不超過|不得超過|最長|至多|最多|以)\s*'
    r'([' + _CNY + r']+|\d{1,2})\s*年'
    r'(?:\s*(?:又|零)?\s*([' + _CNY + r']+|\d{1,2})\s*個?月)?'
    r'(?:\s*(?:為(?:原則|限|上限)|以內|以下))?')
DUR_CTX = re.compile(r'期程|期間|計畫|執行|補助|輔導|年限|原則|辦理|完成|結案|補助期')
DUR_BAD = re.compile(r'折舊|保固|保存|保管|存續|租賃|償還|償付|分期|貸款|屆滿|營運|設立|成立')
# 弱型年份/期程前若接這些字,視為契約/範本條款誤抓,不採用
# (例:近3年、完畢後10年內保管、核定後3個月內收件)
TIME_BOILERPLATE_PRE = re.compile(r'(近|前|完畢後|完成後|核定後|收件日|簽約後|保管|查核|查證|屆滿|存續|逾)$')
# 金額數字類別:阿拉伯 + 國字(不含萬/億,萬元邊界才成立)
_NUMCLS = r'[\d,零〇一二兩三四五六七八九十百千壹貳參叁肆伍陸柒捌玖拾佰仟]'
MONEY_PATTERNS = [
    ("萬元金額", r'(?:新臺幣|新台幣|NT\$?)?\s*' + _NUMCLS + r'+\s*萬元(?:以上|以下|整)?'),
    ("百分比", r'百分之\s*(?:\d+|[' + _CNY + r'百]+)|\d{1,3}(?:\.\d+)?\s*%|\d\s*成'),
    ("元金額", r'(?:新臺幣|新台幣|NT\$?)\s*[\d,]{4,}\s*元'),
]

def _clean(s):
    return re.sub(r'\s+', "", s)

def find_time(text, win=200, weak_ok=True):
    # Pass1: 強型(日期/隨到隨),依錨點可靠度序
    for a in TIME_ANCHORS:
        pos = 0
        while True:
            i = text.find(a, pos)
            if i < 0:
                break
            window = text[i + len(a): i + len(a) + win]
            for typ, pat in TIME_STRONG:
                m = re.search(pat, window)
                if m and m.group(0).strip():
                    ctx = re.sub(r'\s+', " ", text[i: i + len(a) + 60])
                    return a, _clean(m.group(0)), typ, ctx
            pos = i + len(a)
    # Pass1.5: 明確期程限制語(不超過X年/以X年為原則);此為真時程,不受 weak_ok 壓制
    for m in re.finditer(DUR_LIMIT, text):
        around = text[max(0, m.start() - 12): m.end() + 8]
        if DUR_BAD.search(around) or not DUR_CTX.search(around):
            continue
        val = _clean(cn_num_to_ar(m.group(0)))
        return "期程限制語", val, "期程長度", re.sub(r'\s+', " ", around)
    if not weak_ok:   # 契約範本來源:只採日期,duration一律留空
        return "", "", "", ""
    # Pass2: 弱型(期程長度/純年份),過濾契約boilerplate
    for a in TIME_ANCHORS:
        pos = 0
        while True:
            i = text.find(a, pos)
            if i < 0:
                break
            window = text[i + len(a): i + len(a) + win]
            for typ, pat in TIME_WEAK:
                for m in re.finditer(pat, window):
                    pre = window[max(0, m.start() - 20): m.start()]
                    if TIME_BOILERPLATE_PRE.search(pre) or re.search(r'例如|例：|例:|編列|科目|預算|比例|保證|結束日後|請款|月數|之\s*\d+\s*%', pre):
                        continue
                    ctx = re.sub(r'\s+', " ", text[i: i + len(a) + 60])
                    return a, _clean(cn_num_to_ar(m.group(0))), typ, ctx
            pos = i + len(a)
    return "", "", "", ""

def _wan_value(s):
    m = re.search(r'(' + _NUMCLS + r'+)\s*萬', s)
    return to_wan(m.group(1)) if m else None

# 全文找「上限語境」的萬元金額(挖真正補助上限,不只錨點旁;含國字)
# 分支2允許萬元與「為上限/為限/為原則」間夾註記(如(含稅))
CAP_PAT = re.compile(r'(?:上限|最高|至多|不超過|不得超過)[^。；\n]{0,12}?(' + _NUMCLS + r'+)\s*萬元'
                     r'|(' + _NUMCLS + r'+)\s*萬元(?:\s*[(（][^)）。；\n]{0,6}[)）])?\s*(?:為上限|為限|為原則|為限額|整)')
CAP_EXCLUDE = re.compile(r'(資本額|出資額|實收資本|一億|營業額|設備|設施|器材|專利|每項|單價|單筆|每人|雜費|差旅|租金)')

def find_money(text, win=220):
    best = None   # (value, matched, ctx)
    # A) 全文: 上限語境的萬元(含國字),取最高
    for m in re.finditer(CAP_PAT, text):
        num = m.group(1) or m.group(2)
        if not num:
            continue
        pre = text[max(0, m.start() - 14): m.start()]
        if CAP_EXCLUDE.search(pre):
            continue
        v = to_wan(num)
        if v is None or v < 10:   # <10萬視為雜項(專利/差旅等,另有CAP_EXCLUDE把關),非計畫補助上限
            continue
        if best is None or v > best[0]:
            ctx = re.sub(r'\s+', " ", text[max(0, m.start() - 8): m.start() + 28])
            best = (v, f"{v:,}萬元", ctx)
    # B) 金額錨點視窗內的萬元(補漏,取最高)
    for a in MONEY_ANCHORS:
        pos = 0
        while True:
            i = text.find(a, pos)
            if i < 0:
                break
            window = text[i + len(a): i + len(a) + win]
            for m in re.finditer(MONEY_PATTERNS[0][1], window):
                v = _wan_value(m.group(0))
                if v is not None and v >= 20 and (best is None or v > best[0]):
                    ctx = re.sub(r'\s+', " ", text[i: i + len(a) + 40])
                    best = (v, f"{v:,}萬元", ctx)
            pos = i + len(a)
    if best:
        ah = next((a for a in MONEY_ANCHORS if a in text), "補助上限")
        return ah, best[1], "萬元金額", best[2]
    # C) 無萬元 → 錨點附近的百分比/元
    for a in MONEY_ANCHORS:
        pos = 0
        while True:
            i = text.find(a, pos)
            if i < 0:
                break
            window = text[i + len(a): i + len(a) + win]
            for typ, pat in MONEY_PATTERNS[1:]:
                m = re.search(pat, window)
                if m and m.group(0).strip():
                    ctx = re.sub(r'\s+', " ", text[i: i + len(a) + 60])
                    val = norm_pct(m.group(0)) if typ == "百分比" else _clean(m.group(0))
                    return a, val, typ, ctx
            pos = i + len(a)
    # D) 全文: 補助語境的百分比(含國字),供『總經費百分之五十』這類不在錨點旁的
    for m in re.finditer(r'(?:補助|補貼|經費|總經費|最高|上限|至多|補助比[率例])[^。；\n]{0,10}?'
                         r'百分之\s*([' + _CNY + r'百]+|\d+)', text):
        g = m.group(1)
        val = (str(cn2int(g)) if _has_cn(g) else g) + '%'
        ctx = re.sub(r'\s+', " ", text[max(0, m.start() - 6): m.end() + 4])
        return "補助比例", val, "百分比", ctx
    return "", "", "", ""

# 新關鍵字探勘: 找 值token 但前方標籤(含時間/期間/金額等字)不在已知anchors
TIME_LABEL_HINT = re.compile(r'([一-鿿A-Za-z]{2,8}(?:時間|期間|期程|日期|期限|受理|收件|截止|起訖))')
MONEY_LABEL_HINT = re.compile(r'([一-鿿]{0,4}(?:補助|經費|額度|金額|上限|比例|補貼|款項|獎勵)[一-鿿]{0,4})')

def discover_new(text, anchors, value_pat, hint_re):
    found = []
    for m in re.finditer(value_pat, text):
        pre = text[max(0, m.start() - 18): m.start()]
        for lm in hint_re.finditer(pre):
            label = lm.group(1)
            if not any(a in label or label in a for a in anchors) and label not in found:
                found.append(label)
    return found

TIME_VALUE_PAT = r'(?:隨到隨|即日起|額滿為止|1?\d{2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}?\s*日?)'
MONEY_VALUE_PAT = r'[\d,]+\s*萬元|百分之\s*\d+|\d{1,3}\s*%'

# ---------- 計畫名稱: 取內文標題行(比PDF metadata可靠) ----------
GENERIC_TITLE = re.compile(r'^(.{0,3}(署|部|處|局|中心|公司|Microsoft|Word|Adobe|未命名|Untitled|DIGITAL).{0,6})$')
TOC_LINE = re.compile(r'\.{3,}|…|·{3,}|[0-9]\s*$')          # 目錄行(點引導或結尾頁碼)
PREAMBLE = re.compile(r'^.{0,8}(為|特|茲|依據|訂定|應|以)[^，、：。]{0,20}(，|、|：|。)')  # 前言句
CLAUSE = re.compile(r'係?依據.{0,20}(辦法|要點|條)|特(辦理|訂定)|為(鼓勵|協助|推動|輔導|促進)|認定要點|相關法律')  # 條款/前言
def _good_title(l):
    if not (6 <= len(l) <= 45):
        return False
    if re.match(r'^[一二三四五六七八九十壹貳參肆伍陸（(【\d、.※]', l):
        return False
    if TOC_LINE.search(l) or PREAMBLE.match(l) or CLAUSE.search(l):
        return False
    return True
def pick_title(text, meta_title, fname=""):
    fn = re.sub(r'\.(pdf|docx|odt|zip)$', "", (fname or "").strip(), flags=re.I)
    # 0) 原始檔名明確像正式名稱(含申請須知 + 計畫/補助/SBIR/獎勵/研發) → 最可靠
    if fn and "申請須知" in fn and re.search(r'(計畫|補助|SBIR|獎勵|研發)', fn):
        return fn
    lines = [re.sub(r'\s+', "", l) for l in text.splitlines() if l.strip()]
    # 1) 內文含"申請須知"的乾淨標題
    for l in lines[:25]:
        if "申請須知" in l and _good_title(l):
            return l
    # 2) 內文含 計畫/補助/獎勵/要點 的乾淨標題
    for l in lines[:25]:
        if re.search(r'(計畫|補助|作業要點|實施計畫|獎勵)', l) and _good_title(l):
            return l
    # 3) 原始檔名含 計畫/須知/補助
    if fn and re.search(r'(計畫|須知|補助|獎勵|要點)', fn):
        return fn
    # 4) metadata(排除機構名/軟體名)
    mt = (meta_title or "").strip()
    if 4 <= len(mt) <= 45 and not GENERIC_TITLE.match(mt):
        return mt
    # 5) 退回原始檔名 or 第一個尚可行的行
    if fn:
        return fn
    for l in lines[:25]:
        if 6 <= len(l) <= 45 and not TOC_LINE.search(l):
            return l
    return (lines[0][:45] if lines else "")

# ---------- 主流程 ----------
def run(in_csv, out_csv):
    sess = session()
    rows_out = []
    debug_rows = []
    with open(in_csv, encoding="utf-8-sig") as f:
        reader = list(csv.DictReader(f))
    done = set()
    if os.path.exists(out_csv):
        try:
            with open(out_csv, encoding="utf-8-sig") as ef:
                for er in csv.DictReader(ef):
                    u = (er.get("連結") or "").strip()
                    if u:
                        done.add(u)
        except Exception:
            pass
    for idx, row in enumerate(reader, 1):
        dep = (row.get("部門") or "").strip()
        name = (row.get("檔案名稱") or "").strip()
        url = (row.get("連結") or "").strip()
        if url and url in done:
            print(f"[{idx}/{len(reader)}] 去重跳過(已在master)")
            continue
        rec = {"部門": dep, "計畫名稱": "", "原始檔名": name, "檔案類型": "",
               "下載狀態": "", "萃取狀態": "", "時程_命中關鍵字": "", "時程_值": "",
               "時程_型態": "", "金額_命中關鍵字": "", "金額_值": "", "金額_型態": "",
               "備註": "", "連結": url}
        path, ext, st = download(sess, url, dep, name)
        rec["下載狀態"] = st
        rec["檔案類型"] = ext or ""
        if not path:
            rec["萃取狀態"] = "跳過"
            if "網頁" in (st or ""):
                rec["備註"] = "需進頁面找PDF"
            rows_out.append(rec)
            print(f"[{idx}/{len(reader)}] {st} :: {name[:30]}")
            continue
        try:
            text, title = extract_text(path, ext)
        except Exception as e:
            rec["萃取狀態"] = "抽取失敗:" + type(e).__name__
            rows_out.append(rec)
            print(f"[{idx}/{len(reader)}] extract-fail {ext}")
            continue
        text_n = normalize(text)
        if len(text_n.strip()) < 30:
            rec["萃取狀態"] = "疑似掃描/無文字層"
            rec["計畫名稱"] = title
            rows_out.append(rec)
            print(f"[{idx}/{len(reader)}] no-text")
            continue
        rec["萃取狀態"] = "成功"
        rec["計畫名稱"] = pick_title(text, title, name)
        # 時程(日期錨點優先、日期值優先、排契約boilerplate)
        ta, tv, tt, tctx = find_time(text_n, weak_ok=(dep not in TIME_SUPPRESS_WEAK))
        rec["時程_命中關鍵字"], rec["時程_值"], rec["時程_型態"] = ta, tv, tt
        # 金額(取最高上限)
        ma, mv, mt, mctx = find_money(text_n)
        rec["金額_命中關鍵字"], rec["金額_值"], rec["金額_型態"] = ma, mv, mt
        # 備註: 未命中 + 新關鍵字探勘
        notes = []
        if not ta:
            notes.append("時程未命中")
            for nk in discover_new(text_n, TIME_ANCHORS, TIME_VALUE_PAT, TIME_LABEL_HINT)[:3]:
                notes.append("新時程關鍵字?=" + nk)
        if not ma:
            notes.append("金額未命中")
            for nk in discover_new(text_n, MONEY_ANCHORS, MONEY_VALUE_PAT, MONEY_LABEL_HINT)[:3]:
                notes.append("新金額關鍵字?=" + nk)
        rec["備註"] = " / ".join(notes)
        rows_out.append(rec)
        debug_rows.append({"部門": dep, "原始檔名": name, "時程脈絡": tctx, "金額脈絡": mctx})
        print(f"[{idx}/{len(reader)}] OK t={tt or '-'} m={mt or '-'}")

    cols = ["部門", "計畫名稱", "原始檔名", "檔案類型", "下載狀態", "萃取狀態",
            "時程_命中關鍵字", "時程_值", "時程_型態",
            "金額_命中關鍵字", "金額_值", "金額_型態", "備註", "連結"]
    write_header = not os.path.exists(out_csv)
    with open(out_csv, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if write_header:
            w.writeheader()
        for r in rows_out:
            w.writerow(r)
    # debug 脈絡檔(核對用)
    dbg = out_csv.rsplit(".", 1)[0] + "_debug.csv"
    dh = not os.path.exists(dbg)
    with open(dbg, "a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["部門", "原始檔名", "時程脈絡", "金額脈絡"])
        if dh:
            w.writeheader()
        for r in debug_rows:
            w.writerow(r)
    print(f"=== wrote {len(rows_out)} rows to {os.path.basename(out_csv)} ===")

if __name__ == "__main__":
    inp = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "data", "pilot_input.csv")
    outp = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "data", "時程金額萃取結果.csv")
    run(inp, outp)
