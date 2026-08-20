## 1. sme.py — 新增 SBIR 官網來源

- [x] 1.1 探 `https://sbir.org.tw/sbir/dw_apply` 頁面結構，定位申請須知 PDF 連結位置
- [x] 1.2 在 `sites/sme.py` 增加此來源，抓當年度（115）申請須知 PDF
- [x] 1.3 【調查】結論：固定頁、逐年換檔（頁上只放當年度檔），用 has_current_year 自動跟上，不寫死年度
- [x] 1.4 驗證：`_sbir_notices()` 回傳「115年SBIR申請須知.pdf」一筆

## 2. eii.py（→ 改名 ida.py）— 6 個新來源 + 改名

- [x] 2.1 產發局 keid cloud 兩計畫詳情頁（project_description / project_description2）→ PDF 周邊文字含「申請須知」→ 已實作 `_keid_cloud_notices`
- [x] 2.2 【調查】結論：cloud「找補助」目前固定這兩個計畫（project_description[2].aspx 兩固定 URL）；明年若換計畫需更新 URL（型態 A 風險，已註記）
- [x] 2.3 keid citd 兩計畫「計畫申請」下載頁 → download 連結名稱含「申請須知」＋當年度（115/2026）→ 已實作 `_keid_citd_notices`
- [x] 2.4 tdri iddi → 參考文件 → 申請須知 PDF：已寫互動式 render（`render.render_html_click` 點「參考文件」展開）+ `_tdri_notices`（含 115 篩選由關鍵字把關），並接入 `find_notices`。今年 115 已截止、下載下架 → 回 0 筆；程式就緒，明年新一期參考文件重現時自動抓到
- [x] 2.5 nqa News → 當年度公告子頁 → 連結文字含「申請須知」的檔（實為 .docx）→ 已實作 `_nqa_notices`（3 筆）
- [x] 2.6 assist 計畫申請快訊 → 當年度公告子頁 → 附件連結文字含「申請須知」→ 已實作 `_assist_notices`（11 筆：在宅醫療/花蓮災後/原鄉/雲市集/MIT/卓越經營）
- [x] 2.7 tmti news → 逐筆 news_detail 子頁 → 附件 fname 含「申請須知」→ 已實作 `_tmti_notices`（3 筆：關鍵醫材/新北AI化）
- [ ] 2.8 改名 `sites/eii.py` → `sites/ida.py`，同步更新 `run.py` 匯入與 `SITES`（確認站名 key 是否一併改）

## 3. doit.py — A+ 計畫類型各子頁

- [x] 3.1 A+「計畫類型」下 7 子計畫（前瞻技術研發/全球研發創新夥伴/A+STEP/國內研發中心/國際創新研發合作/Fast track/無人機…），各有「資料下載」頁
- [x] 3.2 各子計畫資料下載頁 → 申請須知附件（如「11506前瞻型計畫申請須知」）→ 已實作 `_aiip_datadownload_notices`（動態收集所有「資料下載」連結）
- [x] 3.3 【調查】結論：子計畫會新增（無人機為新），故動態從選單收集「資料下載」連結、不硬編，新子計畫自動納入
- [x] 3.4 驗證通過：`_aiip_datadownload_notices` 抓到全球研發夥伴/前瞻創投/企業布局/國合/快速審查/無人機/無人載具/次世代/A+早創…等多筆申請須知（各×3格式）。小註：資料下載頁混少數 114 年舊須知（11410/11405），主要為 115

## 4. taoyuan.py — 桃園 edb 最新消息（搜尋器）

- [x] 4.1 edb 搜尋打通：ASP.NET postback（action `&Create=1`、按鈕值「送出查詢」、回填 __VIEWSTATE），搜「公告」→ 已實作 `_edb_search`/`_edb_notices`
- [x] 4.2 當年度(115)結果逐筆進子頁，抓附件 title 含「申請須知」的檔（抓到 115 工商展覽補助計畫_申請須知.pdf）

## 5. kaohsiung.py — 高雄 edb 最新消息

- [x] 5.1 edbkcg 列表取含「公告」＋當年度主題 → 已實作 `_edbkcg_notices`
- [x] 5.2 子頁附件 title 含「補助計畫」的 PDF（抓到 2 筆：亞灣進駐/玉竹好店補助計畫；頁尾 boilerplate 自然排除）

## 6. aoc.py — 台灣連鎖加盟協會（taaa）

- [x] 6.1 taaa news/news 逐筆進文章子頁 → 已實作 `_taaa_notices`
- [x] 6.2 篩子頁含「申請須知」的連結（⚠️目前 news/news 只有產業趨勢新聞、無申請須知，回 0 筆；邏輯保留供日後 taaa 貼補助時自動抓）

## 7. taipei.py — 臺北市產業局 doed

- [x] 7.1 doed 內容頁附件 title 含「申請須知」的 PDF → 已實作 `_doed_notices`（3 筆：新創加速器/海外推展貿易/創新創意創業平臺補助計畫）
- [x] 7.2 【調查】結論：檔名不帶年份 → 常設計畫、就地更新，不篩年度、直接抓申請須知

## 8. 新增 cip.py — 原住民族委員會

- [x] 8.1 探明：經濟發展分類列表，公告為 `<hash>-info.html` 子頁，附件 T-<id>.pdf
- [x] 8.2 逐筆進子頁，抓連結文字/title 含「申請須知」的 PDF（現況多為審查結果/核定公告，抓到 1 筆申請須知）
- [x] 8.3 建立 `sites/cip.py`（DEPARTMENT＝原住民族委員會）並註冊進 `run.py` SITES（`--site cip` 可用）

## 9. 新增 moea.py — 經濟部

- [x] 9.1 探明 EE502 Plan?DMN=A00 完整結構：Cloudflare 可過；計畫卡片＝`.content_block`，`onclick="openPlanDesc(id,name)"` 開 modal；modal 分兩分頁「計畫內容」（純文字說明）／「相關文件下載」（`data-bs-target=#contact`，內含 PDF，如「115年度申請須知(含所有附件)」）；下載項是表單 POST（`/Plan/DownSiteFile`，隱藏欄位 `seq`），需真的點按鈕觸發，已實測點擊可下載到真實 PDF；列表分頁 1/2/3（共25筆，JS 分頁非網址翻頁）；卡片上「計畫期程」橫跨多個年度（不只115），需先篩年度才逐一開 modal
- [x] **放棄 9.2/9.3**：使用者決定 moea 不做。結構已完全探明（見 9.1），供之後若要重啟時參考，不建立 `sites/moea.py`

## 10. 收尾驗證

- [ ] 10.1 `--batch all --no-download` 重跑，確認各新來源都出現、且皆為 115 年度
- [ ] 10.2 更新 `md/PALANTIR_SPEC.md` 站點表與 `md/PROGRESS.md`（新增來源、新站、eii→ida 改名）
- [ ] 10.3 回填 4 項調查結論（sme SBIR 頁 / keid 兩計畫 / doit A+ 各計畫 / taipei doed 頁）到對應 adapter 註解
