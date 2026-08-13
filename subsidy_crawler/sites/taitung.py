# -*- coding: utf-8 -*-
"""
sites/taitung.py — 臺東縣 adapter【型態 A / 一般連線 requests】。

臺東下載專區的「檔名就是連結文字」，直接用 notice.links_from 掃出候選，
再交 pick_notices 用（年度＋須知）兩把篩子篩。
"""
from ..common import http, notice

DEPARTMENT = "臺東縣"
LIST_URL = "https://taitungsbir.taitung.gov.tw/Index_Download.aspx?mid=19"


def _candidates(html):
    # 檔名＝連結文字 → 直接用通用掃法
    return notice.links_from(html, LIST_URL)


def find_notices(today=None):
    resp = http.get(LIST_URL)
    return notice.pick_notices(_candidates(resp.text), today=today)
