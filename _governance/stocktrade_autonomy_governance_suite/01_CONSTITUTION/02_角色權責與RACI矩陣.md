# 角色權責與 RACI 矩陣

## 縮寫
- R：Responsible
- A：Accountable
- C：Consulted
- I：Informed

| 工作項 | 你 | ChatGPT | opencode | coding agent | 驗收腳本 | CI/Hook |
|---|---|---|---|---|---|---|
| 定義當前輪主題 | A | R | C | I | I | I |
| 收斂通過標準 | A | R | C | I | C | I |
| 輸出固定模板 | I | C | R | I | I | I |
| 實際改 code | I | I | I | R | I | I |
| 跑測試 | I | I | I | R | C | C |
| 結構驗收 | I | C | I | I | R | C |
| 行為驗收 | I | C | I | I | R | C |
| 流程驗收 | I | C | I | I | R | C |
| 阻擋 commit / push | I | I | I | I | C | R |
| 高風險複審 | A | R | C | I | C | I |
| 最終放行紅區 | A | C | I | I | I | I |
| 判斷升輪 | A | R | C | I | C | I |

## 禁止混權
1. coding agent 不得兼任 pass 裁判。
2. opencode 不得兼任 pass 裁判。
3. 驗收腳本不得擴權直接改 code。
4. CI / Hook 只負責鎖門，不做高階規則解釋。
