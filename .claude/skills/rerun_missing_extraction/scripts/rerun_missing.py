# -*- coding: utf-8 -*-
"""
只重跑「4 種漏抓狀態」的 68 列(使用者人工標記)。
以行號從 stage2/3/4_input.csv 精準選列(避免手抄中文/網址),用快取的 PDF
跑加強版 find_time/find_money(支援國字數字、不超過X年、X萬元為上限),
輸出 data/rerun_result.csv。console 不印中文,全寫檔。

狀態意義:
  S1 時程與金額都有但沒抓到(國字)   -> 需補 時程+金額
  S2 時程沒有、金額有但沒抓到(國字) -> 需補 金額(時程本來就無)
  S3 時程與金額皆有但沒抓到金額     -> 需補 金額
  S4 時程與金額皆有但沒抓到時程     -> 需補 時程
用法: python rerun_missing.py
"""
import os, csv, io, sys, re
import extract_schedule_amount as E

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

# 各 stage 檔的「資料行號」(header=1, 第一筆資料=2) -> 狀態
FLAG = {
    "stage2_input.csv": {
        "S4": [2, 3, 4, 5, 7, 8, 9, 14, 15, 16, 17, 18, 19, 20, 21, 23, 24, 25,
               29, 30, 32, 36, 37, 38, 41, 43, 44, 45, 46, 47, 48, 49, 50, 51,
               54, 55, 56, 58, 59, 61, 62],
    },
    "stage3_input.csv": {
        "S3": [7, 8, 9, 19, 22, 33, 36],       # aoc-485,481,478,444,435,360,323
        "S4": [65, 66, 68, 71, 74, 75],         # service.moea 產業技術司
    },
    "stage4_input.csv": {
        "S1": [8, 9, 10, 11, 12, 13, 16],       # 臺北市產業獎勵補助 + 推薦微型登錄
        "S2": [15, 17, 21],                     # 工商團體參展 + 新創創業平台 + 國發會
        "S3": [25, 27],                         # 桃園工商展覽 + 嘉義市
        "S4": [14, 34],                         # 臺北新創之星 + 苗栗
    },
}
STATUS_DESC = {
    "S1": "時程與金額都有但沒抓到(國字)",
    "S2": "時程沒有金額有但沒抓到(國字)",
    "S3": "時程與金額皆有但沒抓到金額",
    "S4": "時程與金額皆有但沒抓到時程",
}
NEED = {"S1": ("t", "m"), "S2": ("m",), "S3": ("m",), "S4": ("t",)}

# 定向金額覆寫(文件無單一「補助上限」字樣,依使用者指示抓特定款項)
# 值: (關鍵字, 標籤)。關鍵字=None 表示全文最大萬元(排自籌/資本)
OVERRIDE_MONEY = {
    ("stage3_input.csv", 33): (None, "輔導費上限(定向)"),    # aoc-360: 表格輔導費上限取最高
    ("stage3_input.csv", 36): ("輔導款", "輔導款上限(定向)"),  # aoc-323: 輔導款取最高(排自籌款)
}
_WANPAT = re.compile(r'(' + E._NUMCLS + r'+)\s*萬元')

def max_wan(text, kw=None, win=10):
    best = None
    spans = ([(m.start(), m.start() + win + len(kw)) for m in re.finditer(kw, text)]
             if kw else [(0, len(text))])
    for a, b in spans:
        for mm in _WANPAT.finditer(text[a:b]):
            if not kw:
                pre = text[a:][max(0, mm.start() - 6): mm.start()]
                if re.search(r'自籌|資本|股|營業額|實收', pre):
                    continue
            v = E.to_wan(mm.group(1))
            if v and v >= 10 and (best is None or v > best):
                best = v
    return best


def load(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))   # index 0 == 行號2


def main():
    sess = E.session()
    out = []
    counts = {s: [0, 0] for s in STATUS_DESC}   # [補到, 總數]
    for fn, groups in FLAG.items():
        rows = load(os.path.join(DATA, fn))
        for status, lines in groups.items():
            for ln in lines:
                r = rows[ln - 2]
                dep = (r.get("部門") or "").strip()
                name = (r.get("檔案名稱") or "").strip()
                url = (r.get("連結") or "").strip()
                rec = {"來源檔": fn, "行號": ln, "備註狀態": status,
                       "狀態說明": STATUS_DESC[status], "部門": dep, "檔案名稱": name,
                       "時程_命中": "", "時程_值": "", "金額_命中": "", "金額_值": "",
                       "時程脈絡": "", "金額脈絡": "", "是否補到": "", "連結": url}
                path, ext, st = E.download(sess, url, dep, name)
                if not path:
                    rec["是否補到"] = "下載失敗:" + (st or "")
                    out.append(rec)
                    counts[status][1] += 1
                    print(f"[{fn} L{ln} {status}] DL-FAIL {st}")
                    continue
                try:
                    text, _ = E.extract_text(path, ext)
                    tn = E.normalize(text)
                except Exception as ex:
                    rec["是否補到"] = "抽取失敗:" + type(ex).__name__
                    out.append(rec)
                    counts[status][1] += 1
                    print(f"[{fn} L{ln} {status}] EXTRACT-FAIL")
                    continue
                # 重跑一律開放弱型(這些列已知有真實時程)
                ta, tv, tt, tctx = E.find_time(tn, weak_ok=True)
                ma, mv, mt, mctx = E.find_money(tn)
                # 定向金額覆寫(僅在通用抽取沒抓到時)
                if not mv and (fn, ln) in OVERRIDE_MONEY:
                    kw, label = OVERRIDE_MONEY[(fn, ln)]
                    ov = max_wan(tn, kw)
                    if ov:
                        ma, mv, mctx = label, f"{ov:,}萬元", "override:" + (kw or "全文max萬元")
                rec.update({"時程_命中": ta, "時程_值": tv, "金額_命中": ma, "金額_值": mv,
                            "時程脈絡": tctx, "金額脈絡": mctx})
                need = NEED[status]
                got = ((("t" not in need) or bool(tv)) and (("m" not in need) or bool(mv)))
                rec["是否補到"] = "是" if got else "否"
                counts[status][0] += 1 if got else 0
                counts[status][1] += 1
                out.append(rec)
                print(f"[{fn} L{ln} {status}] {'OK' if got else 'MISS'} t={tv or '-'} m={mv or '-'}")

    cols = ["來源檔", "行號", "備註狀態", "狀態說明", "部門", "檔案名稱",
            "時程_命中", "時程_值", "金額_命中", "金額_值",
            "時程脈絡", "金額脈絡", "是否補到", "連結"]
    outp = os.path.join(DATA, "rerun_result.csv")
    with open(outp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in out:
            w.writerow(r)
    total_ok = sum(c[0] for c in counts.values())
    total = sum(c[1] for c in counts.values())
    print("=== summary ===")
    for s in ("S1", "S2", "S3", "S4"):
        print(f"{s}: got {counts[s][0]}/{counts[s][1]}")
    print(f"TOTAL補到 {total_ok}/{total}  -> {os.path.basename(outp)}")


if __name__ == "__main__":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass
    main()
