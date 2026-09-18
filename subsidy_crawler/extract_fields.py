# -*- coding: utf-8 -*-
"""
subsidy_crawler/extract_fields.py — 補助須知 9 欄結構化萃取（主流程）。

用法：
    python -m subsidy_crawler.extract_fields                 # 預設 data/2_dedup_by_filename.csv → data/3_extracted_final.csv
    python -m subsidy_crawler.extract_fields --limit 13      # 只跑去重後前 13 筆（校準用）
    python -m subsidy_crawler.extract_fields --in X.csv --out Y.csv
    python -m subsidy_crawler.extract_fields --in 1_crawled_raw.jsonl --keep-cache

流程：讀輸入清單(部門/檔案名稱/連結；.csv 或 .json/.jsonl 皆可，依副檔名自動判斷)
      → 去重(同URL、排除附件片段檔(附件編號非1開頭)、同計畫多格式擇一優先PDF)
      → 萃取前全文比對去重(同部門兩兩比對原始全文，相似度>=0.99且沒命中申請類別
        守門才判定同一份文件；--skip-fulltext-dedup 可跳過，較耗時)
      → 下載 → 抽字 → normalize → LLM 抽 9 欄 → 申請機關 deterministic 對映
      → (規則交叉檢查旗標) → 寫獨立 data/3_extracted_final.csv + 同路徑 .jsonl。
前提：環境變數 OPENROUTER_API_KEY。輸出可重跑（已在輸出檔的連結會跳過）。
成功列預設自動刪除對應的 pdf_cache 原始檔（--keep-cache 可保留，失敗列一律保留供重跑）。
"""
import os
import io
import sys
import csv
import json
import re
import argparse
import itertools
import collections
from difflib import SequenceMatcher

# Windows console 為 cp950，直接 print 中文會 UnicodeEncodeError → 包成 utf-8。
# 用 encoding 判斷是否已包過（見 run.py 同段註解）：避免 pipeline.py 同行程內多次重包
# 導致前一層 TextIOWrapper 被回收時關掉底層 buffer，後續 print 噴 I/O operation on closed file。
if hasattr(sys.stdout, "buffer") and (sys.stdout.encoding or "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer") and (sys.stderr.encoding or "").lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from .common import textio, llm, trackguard

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
DEFAULT_IN = os.path.join(DATA, "2_dedup_by_filename.csv")
DEFAULT_OUT = os.path.join(DATA, "3_extracted_final.csv")

OUT_COLS = ["部門", "連結", "標題", "描述", "申請機關", "申請資格",
            "補助金額上限", "補助比例", "申請截止日期", "應備資料",
            "申請方式", "諮詢窗口", "萃取模型", "規則交叉檢查", "備註"]

# 規則交叉檢查（find_money/find_time）為最佳努力：能載入就用，不能就略過（非致命）。
try:
    _SKILL = os.path.join(HERE, "..", ".claude", "skills",
                          "extract_schedule_amount", "scripts")
    sys.path.insert(0, os.path.abspath(_SKILL))
    from extract_schedule_amount import find_money, find_time  # noqa
    _HAVE_RULES = True
except Exception:
    _HAVE_RULES = False


# ---------- 申請機關 deterministic 對映（使用者備註 2/5/6）----------
def is_sbir(name, title=""):
    t = (name or "") + " " + (title or "")
    return any(k in t for k in ("SBIR", "sbir", "地方產業創新研發推動", "地方型"))


# 經濟部所屬機關：部門欄若缺「經濟部」前綴，一律補上（備註6）。
# 目前資料裡只有「國際貿易署」缺前綴，其餘 4 個已帶；列全 5 個以防來源變動。
_MOEA_SUBS = ("產業發展署", "商業發展署", "中小及新創企業署", "產業技術司", "國際貿易署")


def agency_of(dep, name, title=""):
    if is_sbir(name, title):
        return "經濟部中小及新創企業署"          # 備註5：SBIR 一律中企署
    if dep.endswith("縣") or dep.endswith("市"):
        return dep + "政府"                     # 非 SBIR 的縣市計畫 → 縣市政府
    core = dep[3:] if dep.startswith("經濟部") else dep
    if core in _MOEA_SUBS:                       # 經濟部所屬署/司 → 確保有「經濟部」前綴
        return "經濟部" + core
    return dep                                  # 其餘（數位發展部、國發會、原民會…）照原名


# ---------- 去重：同 URL + 同計畫多格式擇一（優先 PDF）----------
_FMT_PARENS = re.compile(r"[（(【]?\s*(pdf|odt|docx|doc|odf)\b[^)）】]*[)）】]?", re.I)


def _title_key(dep, name):
    """把檔名正規化成「同一計畫」的 key：去副檔名、去格式標記/下載字樣、去空白標點。"""
    s = (name or "").lower()
    s = re.sub(r"\.(pdf|docx|odt|doc|odf|zip)$", "", s)
    s = s.replace("檔案下載", "").replace("另開視窗", "").replace("下載", "")
    s = _FMT_PARENS.sub("", s)
    s = re.sub(r"[\s、,，。.．\-_/（）()【】「」\[\]]+", "", s)
    return dep + "|" + s


def _prefer_pdf(rows):
    """一組同計畫多格式列，優先回傳 PDF 那列（看副檔名/連結/檔名），否則第一列。"""
    for r in rows:
        blob = (r["連結"] + " " + r["檔案名稱"]).lower()
        if blob.split("?")[0].endswith(".pdf") or "pdf" in blob:
            return r
    return rows[0]


# 檔名含「附件N」且N不是1，才視為單純的附件片段（該排除）：編號從1開始代表這份檔案本身就把
# 須知正文跟前幾號附件合併在一起（如「附件1-3」），是完整版；編號從2號以後才開始（如「附件4-5」
# 「附件6-9」），代表這份只是接續前面的片段、不含正文本體，才是真正該排除的碎片檔。沒有編號、
# 或寫成「及附件」「含附件」這種沒有數字的完整版寫法，都不會被這條規則排除（167筆實測驗證過）。
_ATTACH_FRAG = re.compile(r"附件\s*(\d+)")


def _is_attachment_fragment(name):
    m = _ATTACH_FRAG.search(name or "")
    return bool(m) and int(m.group(1)) != 1


def dedup(rows):
    """rows: [{部門,檔案名稱,連結}] → 去重後同格式。回傳去重列表（保留原順序）。"""
    seen_url = set()
    groups = {}      # title_key -> [row, ...]
    order = []       # title_key 首次出現順序
    for r in rows:
        url = (r.get("連結") or "").strip()
        if not url or url in seen_url:
            continue
        if _is_attachment_fragment(r.get("檔案名稱") or ""):
            print(f"[附件片段排除] {r.get('部門','')}：{(r.get('檔案名稱') or '')[:50]}")
            continue
        seen_url.add(url)
        k = _title_key(r.get("部門", ""), r.get("檔案名稱", ""))
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append({"部門": r.get("部門", "").strip(),
                          "檔案名稱": r.get("檔案名稱", "").strip(),
                          "連結": url})
    return [_prefer_pdf(groups[k]) for k in order]


# ---------- 萃取前全文比對去重（接在檔名判斷之後，LLM萃取之前）----------
FULLTEXT_MERGE_TH = 0.99   # 相似度到這裡、且沒命中申請類別守門，才判定同一份文件、自動省一次LLM
FULLTEXT_REVIEW_TH = 0.3   # 相似度到這裡以上，但沒到自動合併門檻，記錄下來供人工複核
REVIEW_CSV = os.path.join(DATA, "2_fulltext_review_candidates.csv")


def _fulltext_prefilter(todo, keep_cache=False):
    """檔名判斷去重完的 todo，同部門內兩兩比對原始全文相似度：
    相似度>=FULLTEXT_MERGE_TH 且沒命中申請類別守門 -> 判定同一份文件，只留一筆（優先PDF）；
    相似度落在 [FULLTEXT_REVIEW_TH, FULLTEXT_MERGE_TH) 的，不動 todo，
    寫進 REVIEW_CSV 供人工複核、之後視情況補進 trackguard.TRACK_GROUPS。
    下載/抽字失敗的列直接跳過比對，不影響它留在 todo 裡（但會印log，方便事後查是哪個原因
    沒被比對到——這是南投SBIR案例一直查不出原因的洞，這次補上）。"""
    sess = textio.session()
    texts = {}   # 連結 -> 全文
    for r in todo:
        url = r["連結"]
        path, ext, status = textio.download(sess, url, r["部門"], r["檔案名稱"])
        if not path:
            print(f"[萃取前全文比對-下載失敗] {r['部門']}：{r['檔案名稱'][:40]}（{status}）")
            continue
        try:
            text, _ = textio.extract_text(path, ext)
            texts[url] = textio.normalize(text)
        except Exception as ex:
            print(f"[萃取前全文比對-抽字失敗] {r['部門']}：{r['檔案名稱'][:40]}（{type(ex).__name__}）")
        finally:
            if not keep_cache:
                try:
                    os.remove(path)
                except OSError:
                    pass

    by_dept = collections.defaultdict(list)
    for r in todo:
        if r["連結"] in texts:
            by_dept[r["部門"]].append(r)

    to_drop = set()      # 連結，判定為重複、要從 todo 移除的那一筆
    review_rows = []
    for dep, items in by_dept.items():
        for a, b in itertools.combinations(items, 2):
            if a["連結"] in to_drop or b["連結"] in to_drop:
                continue
            ta, tb = texts[a["連結"]], texts[b["連結"]]
            sm = SequenceMatcher(None, ta, tb)
            if sm.quick_ratio() < FULLTEXT_REVIEW_TH:
                print(f"[萃取前全文比對-quick_ratio提早篩掉] {dep}：{a['檔案名稱'][:30]} vs {b['檔案名稱'][:30]}"
                      f"（quick_ratio={sm.quick_ratio():.3f}，真實相似度必定更低）")
                continue
            s = sm.ratio()
            if s < FULLTEXT_REVIEW_TH:
                print(f"[萃取前全文比對-真實相似度過低] {dep}：{a['檔案名稱'][:30]} vs {b['檔案名稱'][:30]}"
                      f"（quick_ratio={sm.quick_ratio():.3f}過關，但真實ratio={s:.3f}未達{FULLTEXT_REVIEW_TH}）")
                continue
            if s >= FULLTEXT_MERGE_TH:
                if trackguard.track_conflict(a["檔案名稱"], b["檔案名稱"]):
                    continue   # 命中已知的申請類別衝突，兩筆都保留
                survivor = _prefer_pdf([a, b])
                loser = b if survivor is a else a
                to_drop.add(loser["連結"])
                print(f"[萃取前全文比對] 判定同一份文件(相似度{s:.3f})，省略：{loser['檔案名稱'][:40]}")
            else:
                review_rows.append({"部門": dep, "全文相似度": round(s, 3),
                                     "標題A": a["檔案名稱"], "連結A": a["連結"],
                                     "標題B": b["檔案名稱"], "連結B": b["連結"]})

    if review_rows:
        write_header = not os.path.exists(REVIEW_CSV)
        with open(REVIEW_CSV, "a", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["部門", "全文相似度", "標題A", "連結A", "標題B", "連結B"])
            if write_header:
                w.writeheader()
            for r in review_rows:
                w.writerow(r)
        print(f"[萃取前全文比對] {len(review_rows)} 組不確定候選，已記錄到 {os.path.basename(REVIEW_CSV)} 供人工複核")

    return [r for r in todo if r["連結"] not in to_drop]


# ---------- 主流程 ----------
def jsonl_path(csv_path):
    """CSV 路徑換成同目錄同檔名的 .jsonl（雙軌輸出用）。"""
    return os.path.splitext(csv_path)[0] + ".jsonl"


def _load_rows(in_path):
    """讀輸入清單：.csv 走既有 csv.DictReader；.json/.jsonl 讀 JSON
    （.jsonl 一行一筆物件、.json 整份 array 皆可）。回傳形狀一律是 [{部門,檔案名稱,連結,...}]。"""
    ext = os.path.splitext(in_path)[1].lower()
    if ext in (".json", ".jsonl"):
        rows = []
        with open(in_path, encoding="utf-8") as f:
            if ext == ".jsonl":
                for line in f:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
            else:
                rows = json.load(f)
        return rows
    with open(in_path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_done(out_csv):
    """只把「成功」（有萃取模型）的連結視為已完成 → 續傳時失敗的會重試。"""
    done = set()
    if os.path.exists(out_csv):
        with open(out_csv, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                u = (row.get("連結") or "").strip()
                if u and (row.get("萃取模型") or "").strip():
                    done.add(u)
    return done


def run(in_csv, out_csv, limit=None, keep_cache=False, skip_fulltext_dedup=False):
    rows = _load_rows(in_csv)
    todo = dedup(rows)
    if not skip_fulltext_dedup:
        todo = _fulltext_prefilter(todo, keep_cache=keep_cache)
    if limit:
        todo = todo[:limit]
    done = load_done(out_csv)
    sess = textio.session()

    out_jsonl = jsonl_path(out_csv)
    write_header = not os.path.exists(out_csv)
    fout = open(out_csv, "a", encoding="utf-8-sig", newline="")
    writer = csv.DictWriter(fout, fieldnames=OUT_COLS)
    if write_header:
        writer.writeheader()
    jout = open(out_jsonl, "a", encoding="utf-8")

    def _emit(rec):
        # 逐列寫完立刻 flush（CSV 與 JSONL 都是），維持既有「中途崩潰不遺失」的續傳安全性。
        writer.writerow(rec); fout.flush()
        jout.write(json.dumps(rec, ensure_ascii=False) + "\n"); jout.flush()

    total = len(todo)
    for idx, r in enumerate(todo, 1):
        dep, name, url = r["部門"], r["檔案名稱"], r["連結"]
        if url in done:
            print(f"[{idx}/{total}] skip(done)")
            continue
        rec = {c: "" for c in OUT_COLS}
        rec["部門"], rec["連結"] = dep, url

        path, ext, st = textio.download(sess, url, dep, name)
        if not path:
            rec["備註"] = "下載失敗:" + (st or "")
            _emit(rec)
            print(f"[{idx}/{total}] download-fail {st}")
            continue
        try:
            text, title0 = textio.extract_text(path, ext)
            text = textio.normalize(text)
        except Exception as ex:
            rec["備註"] = "抽字失敗:" + type(ex).__name__
            _emit(rec)
            print(f"[{idx}/{total}] extract-fail {ext}")
            continue
        if len(text.strip()) < 30:
            rec["備註"] = "疑似掃描/無文字層"
            rec["申請機關"] = agency_of(dep, name, title0)
            _emit(rec)
            print(f"[{idx}/{total}] no-text")
            continue

        hint = llm.hint_for(dep, is_sbir(name, title0))
        data, model, attempts = llm.extract_9(text, dep, name, hint)
        if not data:
            rec["備註"] = "LLM失敗:" + attempts
            rec["申請機關"] = agency_of(dep, name, title0)
            _emit(rec)
            print(f"[{idx}/{total}] llm-fail")
            continue

        for f in llm.LLM_FIELDS:
            rec[f] = data.get(f, "")
        rec["申請機關"] = agency_of(dep, name, data.get("標題", "") or title0)
        rec["萃取模型"] = model

        # 規則交叉檢查旗標（最佳努力）
        if _HAVE_RULES:
            try:
                _, mv, _, _ = find_money(text)
                _, tv, _, _ = find_time(text)
                flags = []
                if mv and mv not in (rec["補助金額上限"] or ""):
                    flags.append(f"規則金額={mv}")
                if tv and tv not in (rec["申請截止日期"] or ""):
                    flags.append(f"規則截止={tv}")
                rec["規則交叉檢查"] = " / ".join(flags)
            except Exception:
                pass

        _emit(rec)
        print(f"[{idx}/{total}] OK model={model}")

        # 已成功寫入終點檔案，該筆原始快取的任務已達成 → 預設清除（--keep-cache 可保留）。
        if not keep_cache:
            try:
                os.remove(path)
            except OSError:
                pass

    fout.close()
    jout.close()
    print(f"=== done, wrote to {os.path.basename(out_csv)} ===")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=DEFAULT_IN)
    ap.add_argument("--out", dest="out", default=DEFAULT_OUT)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--keep-cache", action="store_true",
                    help="成功萃取後保留 pdf_cache 原始檔（預設成功即刪除，除錯/人工核對用才需要保留）")
    ap.add_argument("--skip-fulltext-dedup", action="store_true",
                    help="跳過萃取前的全文比對去重（預設會跑，較耗時；除錯/測試時可加此旗標跳過）")
    a = ap.parse_args()
    run(a.inp, a.out, a.limit, a.keep_cache, a.skip_fulltext_dedup)


if __name__ == "__main__":
    main()
