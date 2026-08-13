"""
deploy.py — 把 React 前端 build 出來並發布到 GitHub Pages（公開 repo palantir）。

一個指令完成：npm run build → 安全掃描 → force-push 到 palantir repo。
GitHub Pages 偵測到 repo 變動後會自動重新發布，約 1-2 分鐘後線上更新。

前置：資料若有變動，要先跑 export_subsidies（那支才碰密碼）。
      這支只搬 build/ 裡已加密的產物，全程不碰密碼。

設計重點：
- 每次在 build/ 內 fresh `git init` → 單一 commit → force-push。
  react-scripts build 每次會清空 build/（連 .git 一起），所以本來就要重新 init，
  這剛好達成「發布 repo 不累積歷史」——加密檔每次因新 salt/IV 全變，
  留歷史會讓 repo 快速膨脹（1000 筆 × 每日推 ≈ 500MB/年）。
- 發布不可逆，push 前做安全掃描，任一項失敗就中止。
- 本環境 console 是 cp950，訊息一律英文（見 extract_schedule_amount/SKILL.md 已知坑 #3）。
"""

import os
import re
import sys
import json
import shutil
import subprocess

# ── 設定 ──────────────────────────────────────────────
REMOTE_URL = "https://github.com/tianhwaservice/palantir.git"
BRANCH = "main"
PAGES_URL = "https://tianhwaservice.github.io/palantir/"
COMMIT_MSG = "deploy: update site"
# ─────────────────────────────────────────────────────

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
REACT_DIR = os.path.join(PROJECT_ROOT, "React")
BUILD_DIR = os.path.join(REACT_DIR, "build")
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")


def run(cmd, cwd, shell=False):
    """跑一個指令，失敗就丟例外並印出來。"""
    print(">>", cmd if isinstance(cmd, str) else " ".join(cmd))
    result = subprocess.run(cmd, cwd=cwd, shell=shell)
    if result.returncode != 0:
        raise RuntimeError("command failed (exit %d): %s" % (result.returncode, cmd))


def read_db_password():
    """讀 .env 的 DB 密碼，之後用來確認 build 產物裡沒有它。"""
    if not os.path.exists(ENV_PATH):
        return None
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("POSTGRES_PASSWORD="):
                return line.split("=", 1)[1].strip()
    return None


def build():
    print("\n=== [1/3] npm run build ===")
    # Windows 上 npm 是 npm.cmd，用 shell=True 讓系統自己解析
    run("npm run build", cwd=REACT_DIR, shell=True)


def safety_scan():
    """發布不可逆，push 前從嚴檢查。任一項失敗就中止。"""
    print("\n=== [2/3] safety scan ===")
    problems = []

    # (a) 必要檔存在
    for name in ("index.html", "subsidies.enc.json"):
        if not os.path.exists(os.path.join(BUILD_DIR, name)):
            problems.append("missing required file: %s" % name)

    # (b) subsidies.enc.json 必須是合法「信封」，不是明文
    enc_path = os.path.join(BUILD_DIR, "subsidies.enc.json")
    if os.path.exists(enc_path):
        try:
            with open(enc_path, "r", encoding="utf-8") as f:
                env = json.load(f)
            for k in ("salt", "iv", "data", "iterations"):
                if k not in env:
                    problems.append("enc.json missing envelope key: %s" % k)
            # 信封裡除了 exported_at 不該有明文欄位
            if "title" in env or "eligibility" in env:
                problems.append("enc.json looks like PLAINTEXT (has data fields!)")
        except Exception as e:
            problems.append("enc.json not valid JSON: %s" % e)

    # (c) 不該出現的敏感檔案/目錄
    for bad in (".env", "src"):
        if os.path.exists(os.path.join(BUILD_DIR, bad)):
            problems.append("build contains sensitive path: %s" % bad)
    py_files = [f for _, _, fs in os.walk(BUILD_DIR) for f in fs if f.endswith(".py")]
    if py_files:
        problems.append("build contains .py files: %s" % py_files)

    # (d) 全檔掃描：不可出現密碼字串
    secrets = ["password123", "POSTGRES_PASSWORD"]
    db_pw = read_db_password()
    if db_pw:
        secrets.append(db_pw)
    for root, _, files in os.walk(BUILD_DIR):
        if ".git" in root:
            continue
        for fn in files:
            if not fn.endswith((".js", ".html", ".css", ".json", ".txt", ".map")):
                continue
            fp = os.path.join(root, fn)
            try:
                content = open(fp, "r", encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            for s in secrets:
                if s and s in content:
                    problems.append("secret '%s' found in %s" % (s, os.path.relpath(fp, BUILD_DIR)))

    if problems:
        print("\n!! SAFETY SCAN FAILED — aborting, nothing pushed:")
        for p in problems:
            print("   - " + p)
        raise SystemExit(1)

    print("   all checks passed (encrypted, no secrets, no source)")


def publish():
    print("\n=== [3/3] publish to GitHub Pages ===")
    git_dir = os.path.join(BUILD_DIR, ".git")
    if os.path.isdir(git_dir):
        shutil.rmtree(git_dir, ignore_errors=True)

    run(["git", "init"], cwd=BUILD_DIR)
    run(["git", "checkout", "-b", BRANCH], cwd=BUILD_DIR)
    run(["git", "add", "-A"], cwd=BUILD_DIR)
    run(["git", "commit", "-m", COMMIT_MSG], cwd=BUILD_DIR)
    run(["git", "remote", "add", "origin", REMOTE_URL], cwd=BUILD_DIR)
    run(["git", "push", "-f", "origin", BRANCH], cwd=BUILD_DIR)


def main():
    if not os.path.isdir(REACT_DIR):
        print("ERROR: React dir not found:", REACT_DIR)
        return 1

    build()
    safety_scan()
    publish()

    print("\n=== DONE ===")
    print("Pushed. GitHub Pages will rebuild in ~1-2 min.")
    print("Live at: " + PAGES_URL)
    print("(colleagues need to refresh / F5 to see the update)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
