# stocktrade 落地接線方案

## 目錄建議
在 repo 根目錄新增：
- `automation/`
- `manifests/`
- `reports/`
- `policy/`
- `scripts/`
- `.githooks/`
- `.github/workflows/`

## 第一批接線
1. 放 `automation/current_round.yaml`
2. 放 `automation/agent_policy.yaml`
3. 放 `scripts/validate_round.py`
4. 放 `scripts/check_forbidden_changes.py`
5. 放 `scripts/check_required_evidence.py`
6. 啟用 pre-commit / pre-push
7. 建 CI `validate-round.yml`

## 第二批接線
1. scheduler
2. opencode 模板
3. review packet
4. escalation flow

## 初期禁止
- 不要讓 agent 自動修改 `server_v2.py`
- 不要自動 push main
- 不要開 live 權限
