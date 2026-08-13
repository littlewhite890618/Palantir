# -*- coding: utf-8 -*-
"""
sites/hualien.py — 花蓮縣 adapter【型態 A / 一般連線 requests】。

花蓮下載頁的「檔名就是連結文字」，所以直接用 notice.links_from 掃出候選
（比金門的 card 解析更簡單），再交 pick_notices 用（年度＋須知）兩把篩子篩。
"""
from ..common import http, notice

DEPARTMENT = "花蓮縣"
LIST_URL = "https://ydc.org.tw/zh-hant/activity/competition/4/"


def _candidates(html):
    # 檔名＝連結文字 → 直接用通用掃法
    return notice.links_from(html, LIST_URL)


def find_notices(today=None):
    resp = http.get(LIST_URL)
    return notice.pick_notices(_candidates(resp.text), today=today)
