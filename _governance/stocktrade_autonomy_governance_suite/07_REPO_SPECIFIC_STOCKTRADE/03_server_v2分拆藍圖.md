# server_v2.py 分拆藍圖

## 現況問題
核心幾乎全塞在單一檔案，造成：
- 權限邊界難切
- 自動修碼難局部化
- 回歸影響面過大
- 不利於機器審核變更範圍

## 建議模組化方向
- `app/api/`
- `app/engine/`
- `app/risk/`
- `app/execution/`
- `app/state/`
- `app/learning/`
- `app/scheduler/`
- `app/contracts/`

## 第一階段拆分順序
1. contracts / schemas
2. validation scripts
3. risk config
4. state machine
5. execution adapter
6. api routes
