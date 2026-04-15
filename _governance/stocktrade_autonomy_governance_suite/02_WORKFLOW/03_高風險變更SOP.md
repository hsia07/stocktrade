# 高風險變更 SOP

## 適用情境
- 紅區檔案變更
- 風控主控
- 狀態機
- broker adapter
- live secrets
- reconciliation

## 步驟
1. 建立 `high_risk_exception_request.md`
2. 說明：
   - 為何必改
   - 影響範圍
   - 風險
   - 回滾方案
   - 驗收方式
3. 先跑模擬 / 測試 / 影響分析
4. 驗收腳本硬審
5. ChatGPT 高階審查
6. 你最終放行
7. 建立候選 PR，不得自動 merge
