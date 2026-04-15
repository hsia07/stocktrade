# TASK_ACTIVE — R-006

## Round
- round_id: R-006
- title: 健康檢查 / 熔斷 / 降級中心
- branch: work/r006-governance

## Objective
只允許治理骨架相關工作，不允許修改核心交易程式。

## Allowed Paths
- manifests/
- reports/
- scripts/
- .githooks/
- .github/workflows/
- automation/

## Forbidden Paths
- server_v2.py
- index_v2.html
- .env
- .env.*
- secrets/
- broker/

## Required Evidence
- reports/run_record.json
- reports/review_packet.md

## Required Checks
- py ./scripts/validation/validate_round.py --manifest ./manifests/current_round.yaml
- py ./scripts/validation/check_forbidden_changes.py --manifest ./manifests/current_round.yaml
- py ./scripts/validation/check_required_evidence.py --manifest ./manifests/current_round.yaml
- py ./scripts/validation/check_commit_message.py --manifest ./manifests/current_round.yaml

## Commit Rule
- commit message 必須以 `R-006` 開頭

## Agent Must Not Decide
- pass_fail
- round_promotion
- live_enable

## Output Requirement
- 只能產生候選 commit
- 不得直接推 master
- 若失敗，必須更新 reports/review_packet.md 與 reports/run_record.json
