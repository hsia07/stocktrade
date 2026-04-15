# Git Gate 與 CI 鎖門法典

## 鎖門順序
1. pre-commit
2. pre-push
3. CI
4. branch protection

## 最低要求
- 未通過驗收不得 push
- 未通過驗收不得合併
- 高風險 PR 不得 auto-merge
- 主分支不得接受未經核准的直接 push
