# 單輪處理 SOP

1. 讀取 `current_round.yaml`
2. 檢查前一輪是否正式通過
3. 由 ChatGPT 輸出：
   - 本輪唯一主題
   - 未通過原因
   - 本次只修
   - 通過標準
   - 禁止事項
4. opencode 轉成固定模板
5. 本地 agent 執行修改
6. 跑本輪驗收腳本
7. 跑回歸驗收
8. 產出：
   - diff
   - fail/pass report
   - run record
   - review packet
9. 高階複審
10. 判定：
   - 留在本輪
   - 合法等待
   - 候選通過
   - 正式通過
