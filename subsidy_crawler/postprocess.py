# -*- coding: utf-8 -*-
"""
subsidy_crawler/postprocess.py — 對 fields_extracted.csv 做輸出層的「篩選 + 去重」。

萃取主流程（extract_fields.py）是可續傳 append，只保證「一連結一列」；但同一計畫常從
不同來源頁/多格式(pdf/odt/docx)被各抓一次，且部分列缺金額與截止日對使用者無益。本模組是
萃取「全部跑完後」的收尾步驟：讀 data/fields_extracted.csv → 篩選 + 去重 → 覆蓋同檔。

處理順序（只作用在「成功列」＝有『萃取模型』者；失敗列原樣保留附在最後）：
  篩選：補助金額上限 與 申請截止日期 兩者皆空 → 移除。
  規則1~4 比對前先做「正規化」（類型A）：標題去空白/去分隔標點、截止日解析成標準日期，
    以吸收 LLM 抽值的機械差異（空白、「-」vs「 」、「115/4/1」vs「115年4月1日」等）。
  去重規則1（同部門）：(部門,標題,金額上限,截止日期) 同 → 含 pdf 就只留 pdf，剩餘>1 隨機留一。
  去重規則2（同部門）：(部門,標題,金額上限,申請資格) 同 → 隨機留一。
  去重規則3（同部門）：(部門,標題,金額上限) 同 → 留截止日期較晚者（多梯次取字串內最晚日期）。
  去重規則4（同部門）：(部門,標題) 同 → 留 標題+金額上限+截止日期 文字總長最長者。
  去重規則5（類型B，同部門）：金額相同 + 應備資料相似度≥0.75（應備太短則退用申請資格≥0.85）
    → 視為「同計畫不同標題」合併。用意在併掉標題長短/前後綴不同、但實為同份的公告
    （如「在宅醫療…應用輔導案」長短標題、「提升商業…計畫」vs「…整合型補助」、大南方前綴等）；
    「金額相同」條件會自動排除同名不同金額的子軌道（多店/單店），避免誤併。

去重一律限「同部門」內（不同縣市同名 SBIR 是不同計畫，不可誤併）。「隨機」用固定 seed
（以群組鍵決定）確保重跑穩定。

用法：
    python -m subsidy_crawler.postprocess              # 覆蓋 data/fields_extracted.csv
    python -m subsidy_crawler.postprocess --dry-run    # 只印統計、不寫檔
    python -m subsidy_crawler.postprocess --in X.csv --out Y.csv
"""
import os
import csv
import re
import glob
import random
import hashlib
import argparse
import collections
from difflib import SequenceMatcher
from urllib.parse import unquote, urlsplit

# 從主流程沿用 15 欄輸出契約；import 會順帶把 stdout 包成 utf-8（Windows cp950 相容），
# 故本檔不再自行包裝 stdout，避免二次包裝造成「I/O operation on closed file」。
from .extract_fields import OUT_COLS
from .common.textio import CACHE

CACHE_ABS = os.path.abspath(CACHE)


# ---------- 檔案類型還原（規則1 需要）----------
def file_ext(url):
    """用連結還原快取檔的副檔名（pdf/docx/odt/zip）。快取檔名 = {safe_name}_{md5(url)[:8]}.{ext}。"""
    h = hashlib.md5((url or "").strip().encode("utf-8")).hexdigest()[:8]
    fs = glob.glob(os.path.join(CACHE_ABS, "*_" + h + ".*"))
    return os.path.splitext(fs[0])[1].lstrip(".").lower() if fs else ""


# ---------- 截止日期解析（規則3「較晚」用）----------
# 支援民國「115年6月1日」「115/6/1」與西元；多梯次取字串內「最晚(最大)」日期代表該列。
_D_FULL = re.compile(r"(\d{2,4})\s*[年/.\-]\s*(\d{1,2})\s*[月/.\-]\s*(\d{1,2})")
_D_YM = re.compile(r"(\d{2,4})\s*[年/.\-]\s*(\d{1,2})\s*月")
_D_Y = re.compile(r"(\d{2,4})\s*年")


def _greg(y):
    y = int(y)
    return y + 1911 if y < 1911 else y      # 民國轉西元（<1911 視為民國年）


def latest_date(s):
    """回傳字串中最晚日期 (year, month, day)；無可解析日期回 None。"""
    if not s:
        return None
    best = None

    def upd(t):
        nonlocal best
        if best is None or t > best:
            best = t

    for m in _D_FULL.finditer(s):
        upd((_greg(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in _D_YM.finditer(s):
        upd((_greg(m.group(1)), int(m.group(2)), 1))
    for m in _D_Y.finditer(s):
        upd((_greg(m.group(1)), 1, 1))
    return best


# ---------- 正規化（類型A：比對用，不改顯示值）----------
# 標題比對前去掉空白與分隔標點（-、─、–、—、·、/、、,，．.），吸收機械差異；保留（）及其內容。
_TITLE_PUNC = re.compile(r"[\s\-─–—・/、,，．.]")


def _ns(s):
    return re.sub(r"\s+", "", s or "")


def _norm_title(s):
    return _TITLE_PUNC.sub("", s or "")


def _norm_amt(s):
    return _ns(s)


def _norm_deadline(s):
    """截止日期比對鍵：能解析出日期就用標準 tuple（吸收格式差異），否則用去空白字串。"""
    d = latest_date(s)
    return ("D",) + d if d else ("S", _ns(s))


def _sim(a, b):
    """去空白後的字元相似度（0~1）。"""
    return SequenceMatcher(None, _ns(a), _ns(b)).ratio()


# ---------- 小工具 ----------
def _g(r, f):
    return (r.get(f) or "").strip()


def _has(r, f):
    return bool(_g(r, f))


def _len3(r):
    """規則3/4 tie-break 用：標題+金額上限+截止日期 文字總長。"""
    return len(_g(r, "標題")) + len(_g(r, "補助金額上限")) + len(_g(r, "申請截止日期"))


def _pick_random(rows, key):
    """群組內隨機留一筆，但以群組鍵當 seed → 重跑結果穩定。"""
    rng = random.Random(repr(key))
    return rng.choice(sorted(rows, key=lambda r: r.get("連結", "")))


def _dedup(rows, keyfunc, selector):
    """依 keyfunc 分群，每群用 selector 選出一筆存活；保留群組首次出現順序。"""
    groups, order = {}, []
    for r in rows:
        k = keyfunc(r)
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(r)
    out = []
    merged = 0
    for k in order:
        g = groups[k]
        if len(g) == 1:
            out.append(g[0])
        else:
            out.append(selector(g, k))
            merged += len(g) - 1
    return out, merged


# ---------- 各規則 selector ----------
def _sel_rule1(g, k):
    pdfs = [r for r in g if file_ext(r.get("連結", "")) == "pdf"]
    cand = pdfs if pdfs else g
    return cand[0] if len(cand) == 1 else _pick_random(cand, k)


def _sel_rule2(g, k):
    return _pick_random(g, k)


def _sel_rule3(g, k):
    # 主鍵：截止日期最晚（None 視為最早）；平手用三欄文字最長。
    def score(r):
        return (latest_date(_g(r, "申請截止日期")) or (0, 0, 0), _len3(r))
    return max(sorted(g, key=lambda r: r.get("連結", "")), key=score)


def _sel_rule4(g, k):
    return max(sorted(g, key=lambda r: r.get("連結", "")), key=_len3)


# ---------- 規則5：類型B 內容相似度合併（同計畫不同標題）----------
SIM_YB = 0.75      # 應備資料相似度門檻（主）
SIM_ZG = 0.85      # 應備太短時退用申請資格的門檻
MIN_BODY = 30      # body 欄位至少這麼長才拿來比（避免空/極短欄誤判為相同）

# 互斥的「申請類別」標記：同計畫的不同申請軌道（須知內容常雷同），不可誤併。
# 這類差異多半只在來源檔名/URL，不在 LLM 抽出的標題裡。
_TRACK_GROUPS = [("個別", "共同", "聯盟"), ("單店", "多店"),
                 ("產品類", "服務類"), ("初階", "進階")]
_NAME_MAP = None


def _name_map():
    """由 data/newnotices3.csv 建 連結→檔案名稱 對映（best-effort，找不到就空）。"""
    global _NAME_MAP
    if _NAME_MAP is None:
        _NAME_MAP = {}
        p = os.path.join(os.path.dirname(CACHE_ABS), "newnotices3.csv")
        if os.path.exists(p):
            with open(p, encoding="utf-8-sig", newline="") as f:
                for r in csv.DictReader(f):
                    u = (r.get("連結") or "").strip()
                    if u:
                        _NAME_MAP[u] = r.get("檔案名稱") or ""
    return _NAME_MAP


def _src_text(r):
    """該列可用來判申請類別的文字＝來源檔名 + URL 檔名 + 標題。"""
    url = _g(r, "連結")
    base = unquote(urlsplit(url).path.rsplit("/", 1)[-1]) if url else ""
    return _name_map().get(url, "") + " " + base + " " + _g(r, "標題")


def _track_conflict(a, b):
    """兩列若各自帶同一組內不同的申請類別標記（個別/共同…）→ 視為不同軌道、不可併。"""
    ta, tb = _src_text(a), _src_text(b)
    for grp in _TRACK_GROUPS:
        ma = {k for k in grp if k in ta}
        mb = {k for k in grp if k in tb}
        if ma and mb and ma != mb:
            return True
    return False


def _same_program(a, b):
    """同金額前提下，判兩列是否同一計畫。
    先要求「標題有包含關係」（正規化後一個是另一個的子字串）——真同計畫多為長短/前後綴標題，
    可排除同金額的姊妹子案（如 服務類 vs 產品類、地方產業 vs 主題式聯盟，互不包含）；
    再要求 body 相似：優先比應備資料，太短則退比申請資格（把應備不像的 AI中央廚房叢擋掉）。"""
    ta, tb = _norm_title(_g(a, "標題")), _norm_title(_g(b, "標題"))
    if not (ta and tb and (ta in tb or tb in ta)):
        return False
    if _track_conflict(a, b):            # 個別/共同、單店/多店… 不同申請軌道 → 不併
        return False
    yba, ybb = _g(a, "應備資料"), _g(b, "應備資料")
    if len(_ns(yba)) >= MIN_BODY and len(_ns(ybb)) >= MIN_BODY:
        return _sim(yba, ybb) >= SIM_YB
    zga, zgb = _g(a, "申請資格"), _g(b, "申請資格")
    if len(_ns(zga)) >= MIN_BODY and len(_ns(zgb)) >= MIN_BODY:
        return _sim(zga, zgb) >= SIM_ZG
    return False


def _sel_cluster(members):
    """cluster 存活者：截止日較晚，平手取三欄文字最長。"""
    def score(r):
        return (latest_date(_g(r, "申請截止日期")) or (0, 0, 0), _len3(r))
    return max(sorted(members, key=lambda r: r.get("連結", "")), key=score)


def _rule5_body(rows):
    """同部門+同金額(非空)內，用 body 相似度做 union-find 分群合併。回傳 (存活列, 併掉數)。"""
    parent = list(range(len(rows)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)

    groups = collections.defaultdict(list)
    for i, r in enumerate(rows):
        amt = _norm_amt(_g(r, "補助金額上限"))
        if amt:                                   # 金額為空者不進比對、各自獨立
            groups[(_g(r, "部門"), amt)].append(i)
    for _, mem in groups.items():
        for a in range(len(mem)):
            for b in range(a + 1, len(mem)):
                if _same_program(rows[mem[a]], rows[mem[b]]):
                    union(mem[a], mem[b])

    clusters = collections.defaultdict(list)
    for i in range(len(rows)):
        clusters[find(i)].append(i)

    out, merged = [], 0
    for root in sorted(clusters, key=lambda r: min(clusters[r])):   # 依首次出現順序
        members = [rows[i] for i in clusters[root]]
        if len(members) == 1:
            out.append(members[0])
        else:
            out.append(_sel_cluster(members))
            merged += len(members) - 1
    return out, merged


# ---------- 主流程 ----------
def filter_and_dedup(success, drop_empty=False):
    """輸入成功列，回傳 (保留列, 統計 dict)。
    drop_empty=True 才啟用「金額上限與截止日期皆空→移除」的篩選（預設關閉、全數保留）。"""
    stats = {"輸入成功列": len(success)}

    # 篩選（可選）：金額上限 與 截止日期 皆空 → 移除
    if drop_empty:
        s1 = [r for r in success if _has(r, "補助金額上限") or _has(r, "申請截止日期")]
        stats["篩選移除(金額+截止皆空)"] = len(success) - len(s1)
    else:
        s1 = success
        stats["篩選移除(金額+截止皆空)"] = 0

    # 去重（皆限同部門；鍵一律含「部門」；標題/截止先正規化＝類型A）
    kt = lambda r: _norm_title(_g(r, "標題"))
    ka = lambda r: _norm_amt(_g(r, "補助金額上限"))
    kd = lambda r: _norm_deadline(_g(r, "申請截止日期"))
    s2, m1 = _dedup(s1, lambda r: (_g(r, "部門"), kt(r), ka(r), kd(r)), _sel_rule1)
    s3, m2 = _dedup(s2, lambda r: (_g(r, "部門"), kt(r), ka(r), _ns(_g(r, "申請資格"))), _sel_rule2)
    s4, m3 = _dedup(s3, lambda r: (_g(r, "部門"), kt(r), ka(r)), _sel_rule3)
    s5, m4 = _dedup(s4, lambda r: (_g(r, "部門"), kt(r)), _sel_rule4)
    s6, m5 = _rule5_body(s5)                                   # 類型B：內容相似度合併

    stats["規則1移除(多格式擇一)"] = m1
    stats["規則2移除(標題+金額+資格同)"] = m2
    stats["規則3移除(標題+金額同,留較晚)"] = m3
    stats["規則4移除(標題同,留最完整)"] = m4
    stats["規則5移除(金額同+應備相似≥0.75)"] = m5
    stats["最終保留成功列"] = len(s6)
    return s6, stats


def run(in_csv, out_csv, dry_run=False, drop_empty=False):
    with open(in_csv, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    success = [r for r in rows if (r.get("萃取模型") or "").strip()]
    failed = [r for r in rows if not (r.get("萃取模型") or "").strip()]

    kept, stats = filter_and_dedup(success, drop_empty=drop_empty)

    print("=== 篩選 + 去重統計 ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"  失敗列(原樣保留): {len(failed)}")
    print(f"  最終總列數: {len(kept) + len(failed)}")

    if dry_run:
        _preview_merges(success)
        print("\n[dry-run] 未寫檔。")
        return

    final = kept + failed
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS)
        w.writeheader()
        for r in final:
            w.writerow({c: r.get(c, "") for c in OUT_COLS})
    print(f"\n已覆蓋寫回 {os.path.basename(out_csv)}（{len(final)} 列）。")


def _preview_merges(success):
    """dry-run：抽樣印出「被去重的同部門+標題群組」供人工審。"""
    import collections
    s1 = [r for r in success if _has(r, "補助金額上限") or _has(r, "申請截止日期")]
    g = collections.defaultdict(list)
    for r in s1:
        g[(_g(r, "部門"), _g(r, "標題"))].append(r)
    dup = {k: v for k, v in g.items() if len(v) > 1}
    print(f"\n--- 篩選後同(部門,標題)重複的群組：{len(dup)} 組 ---")
    for (dep, title), v in sorted(dup.items(), key=lambda x: -len(x[1]))[:12]:
        print(f"[{dep}] {title[:34]} x{len(v)}")
        for r in v:
            print("     ext=%-4s 金額=%-8s 截止=%r" % (
                file_ext(r.get("連結", "")) or "?", _g(r, "補助金額上限") or "(空)",
                _g(r, "申請截止日期")[:46]))


def main():
    HERE = os.path.dirname(os.path.abspath(__file__))
    default_csv = os.path.join(HERE, "data", "fields_extracted.csv")
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=default_csv)
    ap.add_argument("--out", dest="out", default=None, help="預設＝覆蓋輸入檔")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--drop-empty", action="store_true",
                    help="啟用「金額上限與截止日期皆空→移除」篩選（預設關閉、全數保留）")
    a = ap.parse_args()
    run(a.inp, a.out or a.inp, a.dry_run, a.drop_empty)


if __name__ == "__main__":
    main()
