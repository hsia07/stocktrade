# Scheduler Policy

## 目標
scheduler 只負責觸發，不負責宣判通過。

## 必做
- 拉最新 repo
- 檢查是否有新 commit
- 判定是否需要啟動自動流程
- 跑驗收
- 產出報告
- 依失敗分類決定重試 / 升級人工 / 合法等待

## 禁止
- scheduler 不得直接判定升輪
- scheduler 不得直接修改紅區
- scheduler 不得替 agent 宣判通過
- scheduler 不得直接放行高風險 PR

## lease / lock
- 同時間只能有一個活動 run
- 使用 lock file 或 lease record
- lease 過期要有回收機制
