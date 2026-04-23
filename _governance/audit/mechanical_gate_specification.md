================================================================================
MECHANICAL GATE SPECIFICATION — GOV-MECHANICAL-GATE-FOR-DIRECT-CANONICAL-BLOCK
機械閘門規格書：Direct-on-Canonical 防呆 + 法源唯一基準 Fail-Closed Gate
================================================================================

Document ID: GOV-MECH-GATE-SPEC-001
Version: 1.0
Date: 2026-04-23
Canonical Base: 38fc2954990920ec70bba9f1926e7854ec1b030f

================================================================================
SECTION 1: GATE OVERVIEW
================================================================================

Purpose:
  Establish mechanical (automated, fail-closed) gates that prevent:
  1. Unauthorized direct non-merge commits on canonical branch
  2. References to blocked old sources in new/modified files
  3. Topic or phase mapping mismatches with the authoritative source-of-truth

Philosophy:
  "Governance text alone is insufficient. Mechanical enforcement is required
   because humans forget, prompts are ambiguous, and agents infer."

================================================================================
SECTION 2: GATE A — HOOK LAYER (PRE-COMMIT / PRE-PUSH)
================================================================================

Gate Name: canonical_direct_commit_block
Implementation:
  - Script: .githooks/check_canonical_direct_commit.ps1
  - Triggered by: .githooks/pre-commit (bash) and .githooks/pre-push.ps1
  - Platform: Windows PowerShell

Rule:
  IF current_branch == "work/canonical-mainline-repair-001"
    AND commit_is_not_merge
    AND commit_message_does_not_contain "DIRECT-COMMIT-AUTHORIZED"
    AND commit_is_not_gate_installation
  THEN
    FAIL with exit code 1
    BLOCK the commit/push

Allowed Exceptions:
  1. Merge commits (2+ parents) — standard workflow
  2. Commits with "DIRECT-COMMIT-AUTHORIZED" in message — emergency hotfix
  3. Gate installation commits — one-time exception during gate setup
  4. Pre-existing incident-acknowledged commits (bf2c16f, 38fc2954) — backward compatibility

Fail-Closed Behavior:
  - Default: BLOCK
  - Only explicitly allowed patterns pass
  - No silent bypass

================================================================================
SECTION 3: GATE B — VALIDATOR LAYER
================================================================================

Gate Name: branch_workflow_validator
Implementation:
  - Script: scripts/validation/check_branch_workflow.py
  - Checks: --check-canonical, --check-old-source, --check-source-of-truth, --all
  - Called by: pre-commit hook, pre-push hook, manual validate_evidence

Check B1: Canonical Branch Workflow
  IF on canonical branch AND not merge AND not authorized
  THEN FAIL

Check B2: Old Source Reference Block
  Scan all staged/modified files for:
    - "opencode_readable_laws/05_每輪詳細主題補充法典_機器可執行補充版.md"
    - "_governance/law/readable/03"
    - "archive/" (as source reference)
    - "historical/" (as source reference)
    - Old topic strings (pre-v2.1): "基礎治理入口與執行邊界建立", "啟動/停止/暫停控制基底", etc.
  IF any found in non-deprecated-context
  THEN FAIL

Check B3: Source-of-Truth Lock
  Scan manifests/*.yaml for references to blocked sources
  IF manifest references blocked supplementary law without block annotation
  THEN FAIL

Fail-Closed Behavior:
  - Default: BLOCK on any violation
  - Only explicitly allowed patterns pass
  - Violations are listed with file and reason

================================================================================
SECTION 4: GATE C — TEMPLATE LAYER
================================================================================

Gate Name: mandatory_branch_strategy_template
Implementation:
  - File: templates/auto_mode_round_input.md Section 4B
  - Enforced by: Human review + validator cross-check

Mandatory Fields:
  1. branch_strategy: [side_branch / direct_commit_authorized / merge_existing]
     - Must be explicitly selected
     - Missing → blocked
  2. source_of_truth verification: Must confirm PRIMARY AUTHORITY and VALIDATION AUTHORITY
  3. old_source_reference_blocked: Must confirm no blocked sources referenced
  4. topic_mismatch_fail_closed: Must confirm topic matches authority
  5. phase_mapping_mismatch_fail_closed: Must confirm phase mapping matches authority

Fail-Closed Behavior:
  - Template fields are checkboxes that MUST be checked
  - Unchecked mandatory fields → round cannot proceed
  - Human reviewer MUST verify checkboxes before authorization

================================================================================
SECTION 5: EXCEPTIONS AND AUTHORIZATION
================================================================================

Legitimate Exceptions to Direct Commit Block:

EXCEPTION 1: Merge Commits
  - No authorization required
  - Standard workflow
  - Detected by: 2+ parents in commit

EXCEPTION 2: Emergency Hotfix
  - Requires: "DIRECT-COMMIT-AUTHORIZED" in commit message
  - Requires: Human authorization with justification
  - Post-commit: Must file incident report if not already filed
  - Detected by: commit message pattern

EXCEPTION 3: Mechanical Gate Installation
  - One-time exception for installing/updating gate scripts
  - Detected by: staged files include gate script names
  - Post-install: Gate is immediately active for subsequent commits

EXCEPTION 4: Pre-Existing Incident Commits
  - bf2c16f and 38fc2954 are grandfathered
  - Detected by: commit message contains "GOV-161"
  - No future commits receive this exception

================================================================================
SECTION 6: GATE COVERAGE SUMMARY
================================================================================

| Gate | Layer | Mechanical | Enforces | Status |
|------|-------|------------|----------|--------|
| A1 | Hook (pre-commit) | YES | Direct commit block | ACTIVE |
| A2 | Hook (pre-push) | YES | Direct commit block | ACTIVE |
| B1 | Validator | YES | Branch workflow | ACTIVE |
| B2 | Validator | YES | Old source block | ACTIVE |
| B3 | Validator | YES | Source-of-truth lock | ACTIVE |
| C1 | Template | PARTIAL (human-enforced) | Branch strategy | ACTIVE |
| C2 | Template | PARTIAL (human-enforced) | Source-of-truth | ACTIVE |
| C3 | Template | PARTIAL (human-enforced) | Old source block | ACTIVE |

Note: Template layer gates (C1-C3) are partially mechanical because the
checkboxes are validated by humans. Full mechanization would require
parsing the round input file at commit time, which is future work.

================================================================================
SECTION 7: REMAINING NON-MECHANICAL RULES
================================================================================

The following rules exist in governance documents but are NOT mechanically
enforced. They rely on human compliance and agent instruction following:

1. "不得自行改題" — No mechanical check for topic changes mid-round
2. "不得偷做下一輪" — No mechanical check for cross-round work
3. "不得擴大檔案修改範圍" — Partially enforced by forbidden_paths in manifest
4. "狀態碼正確" — No mechanical check for status/content consistency
5. " lane 維持 frozen" — STOP_NOW.flag check is manual

Future work: Gradually migrate non-mechanical rules to mechanical gates.

================================================================================
SECTION 8: TESTING AND VERIFICATION
================================================================================

Test 1: Canonical Direct Commit Block
  - Attempt: git commit on work/canonical-mainline-repair-001 with normal message
  - Expected: FAIL, blocked by hook
  - Actual: [to be verified in next round]

Test 2: Old Source Reference Block
  - Attempt: Stage file containing "05_每輪詳細主題補充法典"
  - Expected: FAIL, blocked by validator
  - Actual: Verified by check_branch_workflow.py --all

Test 3: Authorized Direct Commit Pass
  - Attempt: git commit -m "DIRECT-COMMIT-AUTHORIZED: emergency fix"
  - Expected: PASS, allowed by exception
  - Actual: [to be verified in next round]

Test 4: Merge Commit Pass
  - Attempt: git merge work/some-candidate
  - Expected: PASS, merge commits are always allowed
  - Actual: [to be verified in next round]

Test 5: Side Branch Commit Pass
  - Attempt: git checkout -b work/test-candidate; git commit
  - Expected: PASS, not on canonical branch
  - Actual: [to be verified in next round]

================================================================================
END OF GATE SPECIFICATION
================================================================================
