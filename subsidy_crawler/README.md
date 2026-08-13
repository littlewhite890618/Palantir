# subsidy_crawler

政府補助「申請須知」自動抓取系統（Palantir 後端）。

- 規格：[`../md/PALANTIR_SPEC.md`](../md/PALANTIR_SPEC.md)「Palantir 後端規格」
- 進度：[`../md/PROGRESS.md`](../md/PROGRESS.md)

## 結構
```
common/   共用工具（連線 / 年度 / 找須知 / SQLite / adapter 介面 / 瀏覽器）
sites/    各站 adapter（小抄）
data/     輸出（subsidy.sqlite、notices_*.csv）
run.py    主入口
```

## 怎麼跑
```
python -m subsidy_crawler.run --site kinmen
```
（目前為骨架階段，common/ 與 sites/ 多為 stub，會依 PROGRESS.md 逐步填。）
