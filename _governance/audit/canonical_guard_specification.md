# Canonical Guard Specification (P0)

## Purpose
Mechanized protection for canonical branch to prevent unauthorized direct commits and pushes.

## Guard Rules

### Rule 1: Block single-parent direct commits to canonical
- **Target**: canonical branches (main, work/canonical-*)
- **Block**: Any commit with single parent (non-merge commit) directly on canonical
- **Detection**: Check commit parents count during pre-commit hook
- **Error**: "DIRECT COMMIT BLOCKED: Single-parent commit cannot be made directly on canonical branch"

### Rule 2: Block unauthorized push to canonical
- **Target**: remote canonical branches (origin/main, origin/work/canonical-*)
- **Block**: Any push that is not:
  - Signed merge commit (merge commit with proper evidence)
  - Signed canonical rollback (with explicit user authorization)
  - Force-with-lease correction (with explicit user authorization)
- **Detection**: Check in pre-push hook
- **Error**: "UNAUTHORIZED PUSH BLOCKED: Push to canonical requires proper authorization"

### Rule 3: Legal exceptions
Allowed pushes to canonical:
1. **Signed merge commit**: Merge commit with evidence package in commit
2. **Signed rollback**: Explicit user authorization for `git reset --hard` + force push
3. **Force-with-lease correction**: Explicit user authorization for `git push --force-with-lease`

### Implementation Points
- pre-commit hook: Check if on canonical branch, block single-parent commits
- pre-push hook: Check commit type, verify authorization/evidence
- Evidence required: task.txt, evidence.json, report.json with proper signatures

## Verification
```bash
# Test blocked direct commit
git checkout work/canonical-mainline-repair-001
echo "test" >> test.txt
git add test.txt
git commit -m "direct commit test"  # Should be BLOCKED

# Test allowed merge commit
git merge --no-ff <branch>  # Should be ALLOWED (with evidence)
```

## Related Files
- `.git/hooks/pre-commit` (implements Rule 1)
- `.git/hooks/pre-push` (implements Rule 2)
- `_governance/audit/canonical_guard_specification.md` (this file)
