---
name: catch_cpc
description: 當要抓中國生產力中心（CPC）承辦計畫的申請須知時使用——CPC本身只是執行/顧問單位，計畫列表頁會連到各計畫的外部官方網站，須知要到外部站上抓。屬封存的歷史工具，但邏輯獨立自足，隨時可重跑。
---

# catch_cpc — CPC 承辦計畫→外部官網 抓申請須知

## 用途
中國生產力中心（CPC）是「執行/顧問單位」，不是補助機關。它的計畫列表頁
(`https://www.cpc.org.tw/zh-tw/post/list/2112`) 列出多個計畫，每個計畫連到 CPC 內頁
(`post/contents/{id}`)，內頁再導向各計畫的「外部官方網站」，申請須知就在那些外部站上。

流程：
1. 抓 CPC 計畫列表頁，取出每個計畫卡片（標題 + 內頁連結）
2. 進每個計畫內頁，抽出它連到的外部官方網站（`gov.tw` / `nat.gov.tw` / `org.tw`）
3. 對每個外部站嘗試抓「申請須知」PDF

## 現況
與其他 5 支封存爬蟲不同，這支**不依賴已遺失的中文輸入 CSV**——直接從 CPC 官網即時抓列表，
自足可重跑。

## 執行
```bash
python scripts/cpc_external_notice_crawler.py
```
需求：`pip install requests`

## 已知坑（程式內註解已標明）
- 部分外部站（如 `aoc.gov.tw` 商業發展署）可穩定抓到
- 部分站（CITD `keid.nat.gov.tw`、SIIR `gcis.nat.gov.tw/neo-s`）是老舊 ASP.NET WebForms，
  需 session/viewstate 或已失效，`requests` 難直接抓——遇到這類站需個別處理，不要預期通用邏輯能吃下

## 相關 Skill
- 若要把 CPC 抓到的須知拿去做時程/金額萃取 → 接 `extract_schedule_amount`
