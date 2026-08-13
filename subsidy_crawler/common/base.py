# -*- coding: utf-8 -*-
"""
common/base.py — 站點 adapter 的「統一介面（契約）」。

每個 sites/*.py 就是一個「站點 adapter」。它們是「模組」（不是類別），
只要提供以下東西，run.py 就能一視同仁地使用：

【必須】每個 adapter 都要有：
    DEPARTMENT : str                機關名稱（寫進 CSV，例如 "金門縣"）
    find_notices(today=None)        找出當年度須知檔，回傳 [(檔名, 網址), ...]

【可選】：
    NEEDS_BROWSER_DOWNLOAD : bool    True＝連下載都要用瀏覽器（預設當作 False）

本檔提供：
    check(site)                     驗證一個 adapter 是否符合契約（不符就報清楚的錯）
    department(site)                安全讀 DEPARTMENT
    needs_browser_download(site)    安全讀 NEEDS_BROWSER_DOWNLOAD（沒定義＝False）
"""

# 契約用到的屬性名（集中定義，避免各處手打字串出錯）
ATTR_DEPARTMENT = "DEPARTMENT"
ATTR_FIND_NOTICES = "find_notices"
ATTR_NEEDS_BROWSER_DOWNLOAD = "NEEDS_BROWSER_DOWNLOAD"


def check(site):
    """驗證 site 模組符合 adapter 契約；不符合就 raise TypeError（講清楚缺什麼）。"""
    name = getattr(site, "__name__", repr(site))
    dep = getattr(site, ATTR_DEPARTMENT, None)
    if not isinstance(dep, str) or not dep:
        raise TypeError(f"adapter {name} 缺少字串屬性 {ATTR_DEPARTMENT}")
    fn = getattr(site, ATTR_FIND_NOTICES, None)
    if not callable(fn):
        raise TypeError(f"adapter {name} 缺少函式 {ATTR_FIND_NOTICES}()")
    return True


def department(site):
    """機關名稱。"""
    return getattr(site, ATTR_DEPARTMENT, "")


def needs_browser_download(site):
    """這個站是否連下載都要用瀏覽器（沒定義就當 False）。"""
    return bool(getattr(site, ATTR_NEEDS_BROWSER_DOWNLOAD, False))
