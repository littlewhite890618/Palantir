## Why

人工核對後發現，部分機關除了現有 adapter 已抓的來源外，還有其他官網/計畫頁也放了當年度（115）
的申請須知，目前漏抓。本次針對 8 個機關擴充抓取來源，並新增一個原住民族委員會 adapter，
提升覆蓋率。所有新增來源一律仍只取當前年度（115）資料，判定原則不變。

## What Changes

- **sme.py**：新增 SBIR 官網來源（sbir.org.tw/sbir/dw_apply）找申請須知 PDF；並調查該頁是否逐年更新。
- **eii.py → 改名 ida.py**：新增 6 個來源（產發局 keid 補助前兩計畫、citdweb 兩計畫、tdri iddi、nqa 公告子頁、assist、tmti），並調查其中兩計畫是否逐年固定；檔案改名連帶更新 `run.py` 匯入與 `SITES`。
- **doit.py**：A+ 企業創新研發淬鍊計畫額外抓「計畫類型」下各計畫子頁的資料下載申請須知 PDF；調查這些計畫是否逐年固定。
- **taoyuan.py**：新增 tycg edb 最新消息，用站上搜尋器搜「公告」，逐筆進子頁找含申請須知的 PDF。
- **kaohsiung.py**：新增 kcg edb 最新消息，依序找含「公告」的主題 → 子頁找含「補助計畫」的 PDF。
- **aoc.py**：新增 taaa.org.tw/news/news，逐主題進子頁篩含「申請須知」的連結。
- **taipei.py**：新增 doed.gov.taipei 頁面抓申請須知檔；調查是否逐年更新。
- **新增 adapter（原住民族委員會，cip.gov.tw）**：逐主題找含「申請須知」的 PDF，並註冊進 `run.py`。
- **新增 adapter（經濟部，service.moea.gov.tw/EE502 Plan?DMN=A00）**：依序找頁面內 PDF 格式的申請須知檔，並註冊進 `run.py`。

不改變既有抓取的行為契約，僅擴充來源與新增一站。**BREAKING**：`eii.py` 檔名改為 `ida.py`
（模組匯入路徑改變，需同步改 `run.py`；站名 key 是否一併改由 tasks 決定）。

## Capabilities

### New Capabilities
<!-- 無：本次為既有 subsidy-crawler 能力的實作層來源擴充，行為契約不變。 -->

### Modified Capabilities
<!-- 無 spec 層行為變更。`.openspec.yaml` 已設 skip_specs: true（純實作擴充，不寫 delta）。 -->

## Impact

- **既有 adapter**：`sites/sme.py`、`sites/eii.py`（→ `ida.py`）、`sites/doit.py`、`sites/taoyuan.py`、`sites/kaohsiung.py`、`sites/aoc.py`、`sites/taipei.py`。
- **新增檔**：`sites/cip.py`（原住民族委員會）。
- **主程式**：`run.py`（新增 `cip` 註冊；`eii`→`ida` 匯入與 `SITES` key 更新）。
- **共用層**：可能沿用/擴充 `common/render.py`（部分新站若為 SPA/擋爬需瀏覽器）、`common/notice.py`、`common/year.py`；不改行為。
- **調查產出**：4 個「是否逐年更新/計畫是否會換」的結論（sme SBIR 頁、keid 兩計畫、doit A+ 各計畫、taipei doed 頁），影響各站要寫死年度還是動態偵測。
- 仍**不寫 `subsidies` 表**、仍只取當前年度（115）。
