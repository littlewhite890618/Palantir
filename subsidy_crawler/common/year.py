# -*- coding: utf-8 -*-
"""
common/year.py — 年度判定與「須知」關鍵字。

台灣公文用「民國年」：民國年 = 西元年 − 1911（例如西元 2026 → 民國 115）。
補助案每年換一版，我們只要「當前年度」那一版。跨年之際（年初幾個月），新年度文件
可能還沒發布，所以容忍也接受前一年（近 3 個月）。
"""
import re
from datetime import date

# 一年之始的容忍月數：1~3 月時，也接受前一民國年（新年度文件可能還沒出）。
_ROLLOVER_MONTHS = 3


def current_roc_year(today=None):
    """回傳當前民國年（int）。例：西元 2026 → 115。"""
    today = today or date.today()
    return today.year - 1911


def accepted_roc_years(today=None):
    """回傳「可接受」的民國年集合：當前年；年初 1~3 月時再加上前一年。"""
    today = today or date.today()
    roc = today.year - 1911
    years = {roc}
    if today.month <= _ROLLOVER_MONTHS:
        years.add(roc - 1)
    return years


def has_current_year(text, today=None):
    """text（標題/檔名）裡是否出現「可接受的民國年」，例如『115年…』。"""
    if not text:
        return False
    accepted = accepted_roc_years(today)
    # 找出所有像民國年的三位數（1xx），看有沒有落在可接受集合裡。
    for m in re.findall(r"1\d{2}", text):
        if int(m) in accepted:
            return True
    return False


def is_recent_western_date(date_text, today=None):
    """date_text 是西元日期字串（如「2026/07/29」「2026-07-29」），
    判斷它的年份是否為「當前年度」（同樣套用跨年容忍：1~3月也接受去年）。
    用途：中央機關公告列表常標「公告發布日」（西元格式，非民國年），拿來篩最近公告。
    """
    if not date_text:
        return False
    m = re.search(r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", date_text)
    if not m:
        return False
    today = today or date.today()
    accepted = {today.year}
    if today.month <= _ROLLOVER_MONTHS:
        accepted.add(today.year - 1)
    return int(m.group(1)) in accepted


# 「申請須知類」關鍵字（放寬，不只『申請須知』四字）。
# TODO（鋪完 28 站後複查）：依實際命中精簡冗餘——「須知」已涵蓋「申請須知/徵件須知」；
#   若最終沒有站用到「作業要點/實施計畫/公告事項」，也可一併刪掉。
NOTICE_KEYWORDS = ["申請須知", "作業要點", "徵件須知", "須知", "實施計畫", "公告事項"]
# 反向排除（出現在任何位置即排除）：這些是樣本文件，不是主須知。
NOTICE_NEG_ANYWHERE = ["範例", "範本"]
# 反向排除（僅「開頭」算）：編號附件如「附件G-…同意書」。放開頭才排，
# 避免誤傷「…申請須知及附件…」這種本身就是主須知、只是名稱含「附件」的檔。
NOTICE_NEG_PREFIX = "附件"


def looks_like_notice(name):
    """檔名/標題是否像「須知類」主文件（含須知關鍵字、且非樣本/編號附件）。"""
    if not name:
        return False
    if any(neg in name for neg in NOTICE_NEG_ANYWHERE):   # 範例/範本 → 排除
        return False
    if name.lstrip().startswith(NOTICE_NEG_PREFIX):        # 「附件G-…同意書」開頭 → 排除
        return False
    return any(kw in name for kw in NOTICE_KEYWORDS)
