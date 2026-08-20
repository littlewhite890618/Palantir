# -*- coding: utf-8 -*-
"""
build_report.py — 把任意 CSV 轉成「可搜尋 + 點擊展開」的單頁 HTML。

輸出是自包含 HTML（inline CSS/JS、支援深淺色、手機可讀），適合再用 Artifact 工具發布。
欄位角色可自動偵測，也可用參數覆寫：
  --title-col     每列大標題（預設偵測 標題/title/name/計畫名稱，否則第一欄）
  --tag-col       標題旁的小標籤（預設偵測 部門/機關/申請機關）
  --summary-cols  收合時就顯示的摘要欄，逗號分隔（預設偵測 補助金額上限,補助比例,申請截止日期）
  --fail-col      此欄為空的列視為「未完成」高亮（預設偵測 萃取模型；--fail-col "" 關閉）
  --exclude-cols  展開時不顯示的欄，逗號分隔
  --page-title    頁面大標題（預設＝輸入檔名）
  --out           輸出 HTML（預設＝輸入檔同名 .html）

用法：
  python build_report.py --in fields_extracted.csv
  python build_report.py --in x.csv --out x.html --title-col 標題 --tag-col 部門 \
        --summary-cols 補助金額上限,申請截止日期 --page-title "補助案 9 欄"
"""
import argparse
import csv
import html
import io
import os


def esc(s):
    return html.escape(s or "")


def is_url(v):
    return (v or "").strip().lower().startswith(("http://", "https://"))


CSS = """
:root{--bg:#f4f6f9;--surface:#fff;--surface-2:#eef1f7;--text:#1a2030;--muted:#5a6474;--border:#dce1ea;--accent:#3f52d6;--good:#1c8a5f;--good-soft:rgba(28,138,95,.12);--warn:#a8710f;--warn-soft:rgba(168,113,15,.13);--shadow:0 1px 2px rgba(20,30,60,.04),0 6px 20px rgba(20,30,60,.06)}
@media (prefers-color-scheme:dark){:root{--bg:#0d1016;--surface:#161b25;--surface-2:#1d232f;--text:#e6eaf2;--muted:#98a2b4;--border:#29313f;--accent:#8091f2;--good:#43c489;--good-soft:rgba(67,196,137,.15);--warn:#e0a53a;--warn-soft:rgba(224,165,58,.16);--shadow:0 1px 2px rgba(0,0,0,.3),0 8px 26px rgba(0,0,0,.35)}}
:root[data-theme=dark]{--bg:#0d1016;--surface:#161b25;--surface-2:#1d232f;--text:#e6eaf2;--muted:#98a2b4;--border:#29313f;--accent:#8091f2;--good:#43c489;--good-soft:rgba(67,196,137,.15);--warn:#e0a53a;--warn-soft:rgba(224,165,58,.16);--shadow:0 1px 2px rgba(0,0,0,.3),0 8px 26px rgba(0,0,0,.35)}
:root[data-theme=light]{--bg:#f4f6f9;--surface:#fff;--surface-2:#eef1f7;--text:#1a2030;--muted:#5a6474;--border:#dce1ea;--accent:#3f52d6;--good:#1c8a5f;--good-soft:rgba(28,138,95,.12);--warn:#a8710f;--warn-soft:rgba(168,113,15,.13);--shadow:0 1px 2px rgba(20,30,60,.04),0 6px 20px rgba(20,30,60,.06)}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:"PingFang TC","Noto Sans TC","Microsoft JhengHei","Segoe UI",system-ui,sans-serif;line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:1000px;margin:0 auto;padding:36px 18px 90px}
.eyebrow{font-size:12px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin-bottom:8px}
h1{font-size:clamp(22px,3.6vw,30px);margin:0 0 8px;font-weight:750}
.sub{color:var(--muted);font-size:14px;max-width:70ch}
.stats{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 18px}
.stat{font-size:12.5px;font-weight:600;padding:5px 12px;border-radius:999px;background:var(--surface-2);font-variant-numeric:tabular-nums}
.stat.good{background:var(--good-soft);color:var(--good)}
.stat.warn{background:var(--warn-soft);color:var(--warn)}
.searchbar{position:sticky;top:0;background:var(--bg);padding:11px 0;z-index:5;border-bottom:1px solid var(--border);margin-bottom:6px}
#q{width:100%;font-size:15px;padding:10px 13px;border-radius:10px;border:1px solid var(--border);background:var(--surface);color:var(--text)}
#q:focus{outline:2px solid var(--accent);border-color:transparent}
.hint{font-size:12.5px;color:var(--muted);margin-top:6px}
.hint b{color:var(--text)}
.row{background:var(--surface);border:1px solid var(--border);border-radius:12px;margin-bottom:8px;box-shadow:var(--shadow);overflow:hidden}
.row.fail{border-left:3px solid var(--warn)}
.row-head{padding:12px 15px;cursor:pointer;display:flex;flex-direction:column;gap:4px;user-select:none}
.row-head:hover{background:var(--surface-2)}
.rh-top{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.rh-title{font-size:14.5px;font-weight:700}
.rh-tag{font-size:12px;color:var(--muted);background:var(--surface-2);padding:1px 8px;border-radius:5px;white-space:nowrap}
.rh-tag.warn{color:var(--warn)}
.rh-meta{font-size:12.5px;color:var(--muted);display:flex;flex-wrap:wrap;gap:4px 14px;font-variant-numeric:tabular-nums}
.rh-meta b{color:var(--text);font-weight:600}
.detail{display:none;border-top:1px solid var(--border);padding:4px 0}
.row.open .detail{display:block}
.field{display:grid;grid-template-columns:110px 1fr;gap:4px 14px;padding:9px 15px;border-top:1px solid var(--border);align-items:baseline}
.field:first-child{border-top:none}
dt{font-size:12px;font-weight:600;color:var(--muted)}
dd{margin:0;font-size:13px;white-space:pre-wrap;word-break:break-word}
dd.long{max-height:200px;overflow-y:auto;background:var(--surface-2);border-radius:8px;padding:8px 10px;font-size:12.5px}
dd.empty{color:var(--muted);font-style:italic}
dd a{color:var(--accent);word-break:break-all}
.foot{margin-top:28px;color:var(--muted);font-size:12px;border-top:1px solid var(--border);padding-top:14px}
"""

JS = """<script>
var q=document.getElementById('q'),cnt=document.getElementById('count'),rs=document.querySelectorAll('.row');
document.addEventListener('click',function(e){var h=e.target.closest('.row-head');if(h){h.parentElement.classList.toggle('open');}});
q.addEventListener('input',function(){var s=q.value.trim().toLowerCase(),n=0;rs.forEach(function(r){var show=!s||r.dataset.s.indexOf(s)>=0;r.style.display=show?'':'none';if(show)n++;});cnt.textContent=n;});
</script>"""


def pick(cols, cands):
    for c in cands:
        if c in cols:
            return c
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", default=None)
    ap.add_argument("--page-title", default=None)
    ap.add_argument("--title-col", default=None)
    ap.add_argument("--tag-col", default=None)
    ap.add_argument("--summary-cols", default=None)
    ap.add_argument("--fail-col", default=None)
    ap.add_argument("--exclude-cols", default="")
    a = ap.parse_args()

    with open(a.inp, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    cols = list(rows[0].keys()) if rows else []

    # 自動偵測欄位角色（都可用參數覆寫）；偵測不到就退回通用預設，任何 CSV 都能跑。
    TITLE_CANDS = ["標題", "計畫名稱", "計畫名", "名稱", "項目", "title", "name", "subject", "計畫"]
    TAG_CANDS = ["部門", "機關", "申請機關", "類別", "類型", "分類", "來源", "狀態",
                 "department", "dept", "category", "type", "status", "group"]
    SUMMARY_CANDS = ["補助金額上限", "補助比例", "申請截止日期", "金額", "日期", "截止", "期限",
                     "amount", "date", "deadline", "price", "數量", "count"]
    FAIL_CANDS = ["萃取模型", "狀態", "status"]

    title_col = a.title_col or pick(cols, TITLE_CANDS) or (cols[0] if cols else "")
    tag_col = a.tag_col or pick(cols, TAG_CANDS)
    fail_col = pick(cols, ["萃取模型"]) if a.fail_col is None else (a.fail_col or None)
    if a.summary_cols:
        summary_cols = [c for c in a.summary_cols.split(",") if c in cols]
    else:
        # 補助案欄位優先；否則自動挑最多 3 個看起來像「摘要」的欄（金額/日期/狀態…），
        # 都沒有就不顯示摘要行（純標題卡片）。排除標題/標籤欄本身。
        summary_cols = [c for c in SUMMARY_CANDS if c in cols and c not in (title_col, tag_col)]
        if not summary_cols:
            summary_cols = [c for c in cols
                            if c not in (title_col, tag_col)
                            and any(k in c.lower() for k in ("金額", "日期", "截止", "期限", "狀態",
                                                             "amount", "date", "status", "價", "數"))][:3]
    exclude = {x for x in a.exclude_cols.split(",") if x}
    page_title = a.page_title or os.path.splitext(os.path.basename(a.inp))[0]
    out = a.out or (os.path.splitext(a.inp)[0] + ".html")

    detail_cols = [c for c in cols if c not in ({title_col, tag_col} | exclude)]

    def is_fail(r):
        return bool(fail_col) and not (r.get(fail_col) or "").strip()

    n_total = len(rows)
    n_fail = sum(1 for r in rows if is_fail(r))
    n_ok = n_total - n_fail

    o = io.StringIO()
    o.write("<style>" + CSS + "</style>\n<div class=\"wrap\">\n")
    o.write('<div class="eyebrow">CSV · 可搜尋</div>\n')
    o.write("<h1>%s</h1>\n" % esc(page_title))
    o.write('<p class="sub">共 %d 筆。上方搜尋框可即時篩選；點任一列展開看完整欄位。</p>\n' % n_total)
    o.write('<div class="stats"><span class="stat">共 %d 筆</span>' % n_total)
    if fail_col:
        o.write('<span class="stat good">完成 %d</span><span class="stat warn">未完成 %d</span>' % (n_ok, n_fail))
    o.write('</div>\n')
    o.write('<div class="searchbar"><input id="q" type="search" placeholder="搜尋…" autocomplete="off">')
    o.write('<div class="hint">顯示 <b id="count">%d</b> / %d 筆　·　點列展開</div></div>\n' % (n_total, n_total))

    for r in rows:
        fail = is_fail(r)
        blob = esc(" ".join((r.get(c) or "") for c in cols).lower())
        o.write('<div class="row %s" data-s="%s">' % ("fail" if fail else "", blob))
        o.write('<div class="row-head"><div class="rh-top">')
        o.write('<span class="rh-title">%s</span>' % esc(r.get(title_col) or "(無標題)"))
        if tag_col and (r.get(tag_col) or "").strip():
            o.write('<span class="rh-tag">%s</span>' % esc(r.get(tag_col)))
        if fail:
            o.write('<span class="rh-tag warn">未完成</span>')
        o.write('</div>')
        meta = ["%s <b>%s</b>" % (esc(c), esc(r.get(c))) for c in summary_cols if (r.get(c) or "").strip()]
        if meta:
            o.write('<div class="rh-meta">%s</div>' % "　".join(meta))
        o.write('</div>')  # row-head
        o.write('<dl class="detail">')
        for c in detail_cols:
            v = r.get(c) or ""
            if not v.strip():
                o.write('<div class="field"><dt>%s</dt><dd class="empty">（空）</dd></div>' % esc(c))
            elif is_url(v):
                o.write('<div class="field"><dt>%s</dt><dd><a href="%s">%s</a></dd></div>' % (esc(c), esc(v), esc(v)))
            else:
                cls = "long" if len(v) > 120 else ""
                o.write('<div class="field"><dt>%s</dt><dd class="%s">%s</dd></div>' % (esc(c), cls, esc(v)))
        o.write('</dl></div>\n')

    o.write('<div class="foot">來源：%s · 共 %d 欄 · 欄位值原樣輸出未經摘要。</div>\n' % (esc(os.path.basename(a.inp)), len(cols)))
    o.write('</div>\n')
    o.write(JS)

    with open(out, "w", encoding="utf-8") as f:
        f.write(o.getvalue())
    print("WROTE", out, "rows=", n_total, "cols=", len(cols),
          "| title=", title_col, "tag=", tag_col, "fail=", fail_col, "summary=", summary_cols)


if __name__ == "__main__":
    main()
