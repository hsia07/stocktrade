# Merge-Pre Evidence Gate Specification (P0)

## Purpose
Ensure no merge decision can be made without complete evidence package.

## Evidence Package Requirements

### Minimum Required Files
1. **task.txt**: Task description, scope, constraints, status
2. **evidence.json**: Structured evidence with commit hashes, test results, file changes
3. **report.json**: Human-readable report with summary and implementation details
4. **candidate.diff**: Diff of changes from canonical to candidate
5. **test-results.txt**: Actual test output (must show PASS/FAIL for each test)

### Optional Files (if applicable)
- **no-aider-used.txt**: Required if aider was NOT used (must state "No aider used in this task")
- **event-log.txt**: Timeline of task execution
- **candidate.diff**: Auto-generated diff file

### Validation Rules

#### Rule 1: Evidence package presence
- **Check**: `git ls-tree -r --name-only HEAD` must contain files under `automation/control/candidates/<TASK_NAME>/`
- **Fail**: If no evidence package directory found

#### Rule 2: Required files check
- **Check**: All 5 minimum required files must exist in evidence package
- **Fail**: If any required file missing

#### Rule 3: Test results validity
- **Check**: test-results.txt must contain actual test output
- **Check**: All tests must show PASSED (no FAILED)
- **Fail**: If tests failed or output missing

#### Rule 4: No aider exception
- **Check**: If `aider.log` not present, `no-aider-used.txt` MUST be present
- **Fail**: If aider.log missing and no-aider-used.txt also missing

### Integration Points
- **merge-pre rereview task**: Must verify evidence package before merge decision
- **pre-commit hook**: Should check for evidence package in candidate commits
- **RETURN_TO_CHATGPT**: Must include `candidate_evidence_package_present_true_or_false`

## Usage in Merge-Pre ReReview
```
1. Check branch diff includes evidence package:
   git diff canonical..candidate --name-status | grep "candidates/<TASK_NAME>/"

2. Verify required files:
   git ls-tree -r --name-only HEAD | grep "<TASK_NAME>/"

3. Check test results:
   cat automation/control/candidates/<TASK_NAME>/test-results.txt
```

## Related Files
- `automation/control/evidence_checker.py` (implements validation)
- `_governance/audit/merge_pre_evidence_gate.md` (this file)
