# stocktrade repo 現況與風險摘要

## 現況
此 repo 目前具有以下特徵：
- 啟動入口非常直接，`run.bat` / `start.bat` 直接執行 `python server_v2.py`
- 核心邏輯高度集中於單一後端檔
- 既有治理文件包括 `RISK_RULES.md` 與 `SOURCE_OF_TRUTH.md`

## 風險
1. 單檔高耦合：任何自動修碼都容易外溢
2. 交易核心、風控、API、排程混在一起：難以做細粒度權限
3. 若直接開放 agent 全自動改核心，容易破壞已通過輪次
4. 若沒有機器可讀驗收，規則會漂移
5. 若沒有 hook / CI 鎖門，未通過結果仍可能被推上去

## 建議
- 初期把 `server_v2.py`、`index_v2.html` 視為紅區
- 優先把綠區流程跑穩
- 優先建立 machine-readable manifest 與 evidence chain
