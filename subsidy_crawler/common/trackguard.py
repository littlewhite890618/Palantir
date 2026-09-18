# -*- coding: utf-8 -*-
"""
common/trackguard.py — 申請類別守門：同計畫底下互斥的申請軌道/分類標記。

跨 extract_fields.py（萃取前的全文比對去重）與 postprocess.py（萃取後規則1~5
的去重）共用同一份清單，避免兩邊各自維護、日後改一邊忘了改另一邊而失去同步。

清單內容都是從真實資料裡踩到誤合併風險才加進來的，不是預先窮舉：
個別/共同/聯盟/主題式（臺南SBIR）、單店/多店（提升商業服務業韌性計畫）、
產品類/服務類/主題式（在宅醫療、高齡計畫）、初階/進階、
新興育成/產業高值/創新優化（產業升級創新平台輔導計畫）。
"""

TRACK_GROUPS = [("個別", "共同", "聯盟", "主題式"), ("單店", "多店"),
                ("產品類", "服務類", "主題式"), ("初階", "進階"),
                ("新興育成", "產業高值", "創新優化")]


def track_conflict(text_a, text_b):
    """兩段來源文字，若各自命中同一組內不同的標記 → 視為不同申請軌道，不可併。"""
    for grp in TRACK_GROUPS:
        ma = {k for k in grp if k in text_a}
        mb = {k for k in grp if k in text_b}
        if ma and mb and ma != mb:
            return True
    return False
