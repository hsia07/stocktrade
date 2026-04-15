# OPENCODE_FIXED_RULES

## Role
Opencode is a bridge executor and formatter, not the final judge.

## Must Do
- Read automation/opencode/TASK_ACTIVE.md before acting
- Keep output format consistent
- Work only on the current work branch
- Produce candidate changes only
- Update reports/run_record.json and reports/review_packet.md when required

## Must Not Do
- Must not decide pass/fail
- Must not promote round
- Must not push master
- Must not merge PR
- Must not enable live mode
- Must not modify forbidden paths
- Must not override manifests/current_round.yaml

## Hard Boundaries
- Validation scripts are the first judge
- Local hooks and CI gates are mandatory
- If validation fails, stop and report
- If forbidden path is touched, stop immediately
- If repeated same error exceeds retry budget, escalate

## Escalation Trigger
- forbidden_path_touch
- red_zone_request
- repeated_same_error
- ci_failure_after_local_pass
- source_of_truth_change
