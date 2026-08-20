# -*- coding: utf-8 -*-
"""
subsidy_crawler/extract_fields.py — 補助須知 9 欄結構化萃取（主流程）。

用法：
    python -m subsidy_crawler.extract_fields                 # 預設 data/newnotices3.csv → data/fields_extracted.csv
    python -m subsidy_crawler.extract_fields --limit 13      # 只跑去重後前 13 筆（校準用）
    python -m subsidy_crawler.extract_fields --in X.csv --out Y.csv

流程：讀輸入 CSV(部門/檔案名稱/連結) → 去重(同URL、同計畫多格式擇一優先PDF)
      → 下載 → 抽字 → normalize → LLM 抽 9 欄 → 申請機關 deterministic 對映
      → (規則交叉檢查旗標) → 寫獨立 data/fields_extracted.csv（不動 year_check）。
前提：環境變數 OPENROUTER_API_KEY。輸出可重跑（已在輸出檔的連結會跳過）。
"""
import os
import io
import sys
import csv
import re
import argparse

# Windows console 為 cp950，直接 print 中文會 UnicodeEncodeError → 包成 utf-8。
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from .common import textio, llm

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
DEFAULT_IN = os.path.join(DATA, "newnotices3.csv")
DEFAULT_OUT = os.path.join(DATA, "fields_extracted.csv")

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


def dedup(rows):
    """rows: [{部門,檔案名稱,連結}] → 去重後同格式。回傳去重列表（保留原順序）。"""
    seen_url = set()
    groups = {}      # title_key -> [row, ...]
    order = []       # title_key 首次出現順序
    for r in rows:
        url = (r.get("連結") or "").strip()
        if not url or url in seen_url:
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


# ---------- 主流程 ----------
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


def run(in_csv, out_csv, limit=None):
    with open(in_csv, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    todo = dedup(rows)
    if limit:
        todo = todo[:limit]
    done = load_done(out_csv)
    sess = textio.session()

    write_header = not os.path.exists(out_csv)
    fout = open(out_csv, "a", encoding="utf-8-sig", newline="")
    writer = csv.DictWriter(fout, fieldnames=OUT_COLS)
    if write_header:
        writer.writeheader()

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
            writer.writerow(rec); fout.flush()
            print(f"[{idx}/{total}] download-fail {st}")
            continue
        try:
            text, title0 = textio.extract_text(path, ext)
            text = textio.normalize(text)
        except Exception as ex:
            rec["備註"] = "抽字失敗:" + type(ex).__name__
            writer.writerow(rec); fout.flush()
            print(f"[{idx}/{total}] extract-fail {ext}")
            continue
        if len(text.strip()) < 30:
            rec["備註"] = "疑似掃描/無文字層"
            rec["申請機關"] = agency_of(dep, name, title0)
            writer.writerow(rec); fout.flush()
            print(f"[{idx}/{total}] no-text")
            continue

        hint = llm.hint_for(dep, is_sbir(name, title0))
        data, model, attempts = llm.extract_9(text, dep, name, hint)
        if not data:
            rec["備註"] = "LLM失敗:" + attempts
            rec["申請機關"] = agency_of(dep, name, title0)
            writer.writerow(rec); fout.flush()
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

        writer.writerow(rec); fout.flush()
        print(f"[{idx}/{total}] OK model={model}")

    fout.close()
    print(f"=== done, wrote to {os.path.basename(out_csv)} ===")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default=DEFAULT_IN)
    ap.add_argument("--out", dest="out", default=DEFAULT_OUT)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    run(a.inp, a.out, a.limit)


if __name__ == "__main__":
    main()
