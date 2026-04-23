# Phase 2 Batch Review Law
## API Auto-Mode Governance Chain — Governance Meta-Law

**Document Version:** 1.0
**Status:** ACTIVE — governance rules in force
**Effective Since:** Phase 2 hygiene alignment (c980ef7)
**Scope:** API-based auto-mode governance chain (OpenAI API ↔ OpenCode ↔ Telegram bot)
**Applicable Phases:** Phase 2 (R017–R048) and all subsequent phases

---

## IMPORTANT — SCOPE BOUNDARY

This law governs the **API-based auto-mode governance chain** (OpenAI API ↔ OpenCode ↔ Telegram bot orchestration loop).

**This law does NOT cover:**
- R017 (秘密與金鑰管理 / Trading broker credentials) — governed by separate round-specific law
- Phase 2 per-round implementation (R017–R048) — each governed by its own round-specific law
- Phase 1 (R001–R016) — already closed, governed by prior law

**This law does NOT replace:**
- 03_161輪逐輪施行細則法典 (round-specific implementation rules)
- R017 secrets management requirements
- Any other Phase 2 round-specific requirements

---

## CHAPTER 1: Authorization Chain and Role Division

### 1.1 Role Hierarchy

The authorization chain follows this hierarchy (highest authority first):

1. **Human** — explicit authorization required for: lane release, Phase 2 entry, per-round authorization, auto-mode release, rollback, containment override
2. **Mechanical Guard** — automated enforcement of governance rules; cannot be bypassed without explicit authorization
3. **OpenCode Agent** — primary contractor for task execution, must comply with mechanical guards
4. **Validator Scripts** — automated compliance verification (check_branch_workflow.py, check_forbidden_changes.py, check_required_evidence.py, validate_evidence.py, validate_round.py)
5. **Telegram Bot** — notification and approval channel for human decisions

### 1.2 Role Definitions

| Role | Responsibility | Authority |
|------|---------------|-----------|
| Human | Explicit authorization, rollback decisions, containment override | Highest |
| OpenCode Agent | Execute rounds per governance rules, produce RETURN_TO_CHATGPT | Execution only |
| Validator Scripts | Verify compliance, block violations | Blocking only |
| Telegram Bot | Relay notifications, collect human decisions | Communication only |
| Canonical Mainline | Target for all merged work; read-only reference | Source of truth |

### 1.3 Authorization Chain

```
Human Authorization
    ↓
Lane Release (STOP_NOW.flag removal)
    ↓
Phase 2 Entry Authorization (per-round)
    ↓
Auto-Mode Release Authorization (separate from Phase 2 entry)
    ↓
Per-Round Authorization (merge-pre, merge, push)
    ↓
Evidence Review → Telegram Report
    ↓
Human Decision for Next Round
```

Each authorization step is **independent**. Approval of one step does NOT imply approval of any subsequent step.

---

## CHAPTER 2: API Orchestration Chain Entry/Exit Definition

### 2.1 Entry Conditions (Batch Execution Start)

All of the following must be true before API auto-mode batch execution begins:

1. Lane released (STOP_NOW.flag removed; confirmed absent)
2. Phase 2 entry authorized by human
3. Auto-mode release authorized by human (separate authorization)
4. state.runtime.json aligned to current round
5. current_round.yaml reflects current round with start_authorized: true
6. Canonical HEAD at last known good state
7. No STOP_NOW.flag present
8. All validator scripts pass at current HEAD

### 2.2 Chain Flow (Normal Operation)

```
Telegram Trigger
    ↓
OpenCode Task Dispatch (round_id, task_type from current_round.yaml)
    ↓
Round Execution
    ↓
Candidate Creation (work/{round_id}-candidate)
    ↓
RETURN_TO_CHATGPT Production
    ↓
Merge-Pre Review
    ↓
Merge Authorization (human)
    ↓
Merge Execution
    ↓
Push Authorization (human)
    ↓
Push Execution (--force-with-lease only)
    ↓
Evidence Review
    ↓
Telegram Report (round_id, status, blockers, next_action)
    ↓
Await Human Decision for Next Round
```

### 2.3 Exit Conditions

**Normal exit**: Round complete → evidence on canonical → Telegram report → await next authorization

**Blocked exit**: First BLOCKED item → batch stop → containment → Telegram alert with failure_point → await human decision

**Emergency exit**: Repeated failure breaker triggered → lane re-frozen → await human decision

---

## CHAPTER 3: Per-Round Admission Criteria (Batch Entry Gate)

All of the following must be verified before a round is admitted into the batch execution:

### 3.1 Round Identity

- [ ] round_id in task description matches round_id in current_round.yaml
- [ ] round_id is the next sequential round (no skipped rounds)
- [ ] Manifest exists at: manifests/{lowercase_round_id}_*.yaml or manifests/current_round.yaml

### 3.2 Candidate Structure

- [ ] Candidate branch named: work/{round_id}-candidate
- [ ] Candidate branch has exactly one commit
- [ ] Candidate commit has canonical HEAD as its only parent
- [ ] No intermediate commits on candidate branch

### 3.3 Manifest Requirements

- [ ] Manifest schema valid (validate_round.py passes)
- [ ] start_authorized: true in manifest
- [ ] required_evidence list complete and files exist
- [ ] required_checks list complete and all validators defined
- [ ] direct_fail_conditions list complete
- [ ] allowed_paths and forbidden_paths properly defined

### 3.4 Evidence Structure

- [ ] automation/control/candidates/{round_id}/task.txt exists
- [ ] automation/control/candidates/{round_id}/report.json exists
- [ ] automation/control/candidates/{round_id}/evidence.json exists
- [ ] automation/control/candidates/{round_id}/candidate.diff exists
- [ ] All evidence files tracked in git (not untracked)

### 3.5 Admission Gate Result

**Pass**: All admission criteria met → round admitted to batch execution

**Fail**: Any admission criterion unmet → BLOCKED; batch stops; Telegram alert; await human

---

## CHAPTER 4: Single-Round Failure = Batch Fail-Closed Stop

### 4.1 Fail-Closed Principle

**RULE**: Any blocked validator, failed check, or governance error in any single round causes the **entire batch to stop immediately**.

### 4.2 Failure Triggers

The batch must stop (fail-closed) when ANY of the following occurs:

- [ ] check_branch_workflow.py returns non-zero exit
- [ ] check_forbidden_changes.py returns non-zero exit
- [ ] check_required_evidence.py returns non-zero exit
- [ ] validate_evidence.py returns non-zero exit
- [ ] validate_round.py returns non-zero exit
- [ ] RETURN_TO_CHATGPT missing required fields
- [ ] formal_status_code is neither "manual_review_completed" nor "blocked"
- [ ] Evidence shows packaging-only (no real work)
- [ ] Forbidden file modified
- [ ] Candidate branch not named correctly
- [ ] Canonical direct commit detected
- [ ] merge-pre rereview not completed before merge
- [ ] --no-verify used in any git operation
- [ ] push without --force-with-lease

### 4.3 Batch Stop Behavior

When batch stops:
1. **Stop immediately**: Do not execute next step in chain
2. **Preserve state**: Full evidence of failure point must be preserved
3. **No retry**: No automatic retry or skip to next round
4. **Telegram alert**: Send alert with failure_point, executed_command, stdout, stderr
5. **Await human**: Human must explicitly authorize next action (retry, abort, or rollback)

---

## CHAPTER 5: Repeated-Failure Breaker

### 5.1 Repeated Failure Trigger

**Trigger**: If the same round fails 3 times consecutively with the same error pattern (same validator, same failure_point)

### 5.2 Detection

- Track: round_id + formal_status_code + failure_point hash
- After 3 consecutive failures with identical failure_point → breaker triggered

### 5.3 Breaker Actions

When breaker triggers:
1. **Lane re-freeze**: STOP_NOW.flag recreated immediately
2. **Batch halt**: All running operations stopped
3. **Telegram alert**: "Repeated failure breaker triggered: round_id={id}, pattern={hash}, count=3"
4. **Containment mode**: No further batch execution until human decision
5. **Evidence preserved**: Full failure chain preserved for review

### 5.4 Recovery

- After human intervention (root cause fix or round abandonment), breaker count resets
- Human must explicitly re-authorize lane release to resume

---

## CHAPTER 6: RETURN_TO_CHATGPT Completeness Control

### 6.1 Required Fields by Task Type

Every task execution must produce a RETURN_TO_CHATGPT document. Missing any required field = BLOCKED.

| Task Type | Required Fields |
|-----------|-----------------|
| merge_pre_rereview | round_id, status, formal_status_code, blockers_found, next_action, validation_summary |
| local_merge_execution | round_id, status, formal_status_code, merge_executed, merge_commit, files_modified, blockers_found, next_action |
| remote_push_execution | round_id, status, formal_status_code, force_push_executed, remote_head_after_push, no_verify_used, blockers_found |
| decision_audit | round_id, status, formal_status_code, (topic-specific required fields), next_action |
| candidate_draft | round_id, status, formal_status_code, files_modified, validation_summary, candidate_branch, candidate_commit |

### 6.2 Formal Status Code Rules

| Code | Meaning | Requires |
|------|---------|----------|
| manual_review_completed | All checks passed; human decision required | Yes — status must be "completed" |
| blocked | Task failed at some point | Yes — status must be "failed" |

**Forbidden**: Any other formal_status_code value. Any return with status="completed" but without formal_status_code="manual_review_completed" = BLOCKED.

### 6.3 Blocked Reporting Requirements

When formal_status_code = "blocked", RETURN_TO_CHATGPT must also contain:
- executed_command
- stdout
- stderr
- failure_point
- remote_head_observed (for push tasks)

Missing any of these fields when blocked = BLOCKED.

---

## CHAPTER 7: Evidence/Manifest Completeness Control

### 7.1 Evidence Package Requirements

Every candidate must have a complete evidence package:

- [ ] **task.txt**: Round identification, task type, summary of work
- [ ] **report.json**: Machine-readable summary with all required fields
- [ ] **evidence.json**: Contains work_done array (min 1 item, non-packaging), validation result, formal_status_code
- [ ] **candidate.diff**: Documents actual code changes; must show positive task count indicator

### 7.2 work_done Array Rules (evidence.json)

The work_done array in evidence.json must contain at least 1 item describing actual work. Items that are purely descriptive of evidence structure (e.g., "evidence package created") do NOT count. Items describing actual code/logic changes DO count.

### 7.3 candidate.diff Rules

- Must show positive task count (zero工作量應視為blocked)
- Must show actual file changes (not just evidence files)

### 7.4 Manifest Validation

- validate_round.py must pass (schema valid)
- All required_checks must be defined and executable
- All required_evidence files must exist and be tracked

### 7.5 Manifest Completeness Check

Before merge, all evidence files must be tracked in git (git add executed). Untracked evidence files = BLOCKED.

---

## CHAPTER 8: Canonical Direct Write Prohibition

### 8.1 Critical Prohibition

**CRITICAL RULE**: Direct commits to the canonical branch (work/canonical-mainline-repair-001) are strictly PROHIBITED.

### 8.2 Allowed Operations on Canonical

| Operation | Allowed? | Conditions |
|-----------|----------|------------|
| git merge (from candidate branch) | YES | Non-squash OR squash with explicit authorization; merge-pre rereview completed |
| git merge --no-ff | YES | With explicit authorization |
| git merge --squash | YES | With explicit authorization only |
| git push | YES | Only --force-with-lease; --no-verify BLOCKED |
| git push --force | NO | BLOCKED |
| git push --force-with-lease | YES | Preferred for canonical recovery |
| git commit directly on canonical | NO | BLOCKED |
| git reset --hard on canonical | NO | BLOCKED (revert via new merge only) |

### 8.3 Detection

check_branch_workflow.py detects canonical direct commits via:
- Verifying candidate commits have canonical as their parent
- Blocking any merge that does not originate from a candidate branch

### 8.4 Consequence

Detection of a direct commit on canonical → immediate containment trigger (see Chapter 10).

---

## CHAPTER 9: Merge / Push / Lane / Phase Start — Separation of Authorization

### 9.1 Authorization Independence

Each of the following is a **legally distinct authorization**. Approval of one does NOT imply approval of any other:

| Authorization | Definition | Triggers |
|--------------|-----------|----------|
| **Lane Release** | Removal of STOP_NOW.flag; enables automation engine to run | Human explicit authorization required |
| **Phase 2 Entry** | Beginning of R017 (first Phase 2 round) | Human explicit authorization required |
| **Auto-Mode Release** | Enabling automated round execution without per-round human sign-off | Human explicit authorization required (separate from lane release) |
| **Per-Round Merge** | Merge of candidate into canonical | Human explicit authorization required |
| **Per-Round Push** | Push of canonical to remote | Human explicit authorization required |
| **Rollback** | git reset --hard to previous known good state | Human explicit authorization required |
| **Containment Override** | Resume from containment without resolving root cause | Human explicit authorization required |

### 9.2 No-Verify Prohibition

**CRITICAL**: --no-verify on any git operation = BLOCKED. This applies to all git commands: commit, merge, push, reset, etc.

### 9.3 Push Requirements

- Only --force-with-lease is permitted for push to canonical
- Pre-push hook validation must pass
- Hook must not be bypassed

---

## CHAPTER 10: Rollback and Containment Conditions

### 10.1 Containment Trigger Conditions

Containment (lane re-freeze + batch halt) is triggered by ANY of:

- [ ] Direct commit on canonical detected
- [ ] Validator consistently failing (3x repeated failure — Chapter 5)
- [ ] Evidence package shows packaging-only (validate_evidence.py fails)
- [ ] Forbidden file modified (check_forbidden_changes.py fails)
- [ ] --no-verify used in any git operation
- [ ] merge without merge-pre rereview completed
- [ ] Canonical HEAD drift without authorization
- [ ] Unexpected git state inconsistent with governance records
- [ ] Telegram API failure during critical notification
- [ ] OpenAI API failure during critical execution step

### 10.2 Containment Actions (Sequential)

1. **Immediate halt**: Stop all running operations
2. **Lane freeze**: STOP_NOW.flag recreated (if absent)
3. **Evidence preservation**: Full state of failure point documented
4. **Telegram alert**: Containment reason + failure_point + evidence summary
5. **Human notification**: Explicit message requiring human decision
6. **Await human**: No automatic resumption

### 10.3 Rollback Conditions

Rollback (git reset --hard) is only permitted when:
- Human explicitly authorizes rollback
- Rollback target is a known good canonical commit (verified merge commit)
- Containment state is documented
- Telegram alert confirms rollback execution

### 10.4 Rollback Prohibition

- Rollback to a non-merge commit = BLOCKED
- Rollback without human authorization = BLOCKED
- Rollback to a commit that breaks merge chain = BLOCKED

---

## CHAPTER 11: Telegram / Review Reporting Traceability

### 11.1 Required Reporting

Every batch execution must produce a Telegram report covering:

| Field | Required |
|-------|----------|
| round_id | YES |
| task_type | YES |
| status | YES |
| formal_status_code | YES |
| blockers_found | YES (if any) |
| evidence_summary | YES |
| next_action | YES |
| timestamp | YES |

### 11.2 Prohibited in Telegram Reports

The following MUST NOT appear in any Telegram report:
- SHIOAJI_API_KEY or SHIOAJI_SECRET_KEY values
- SHIOAJI_CERT_PASS values
- .env file contents
- Any broker credential values
- OpenAI API keys (if used)
- Full error stack traces containing credential context

### 11.3 Telegram Alert Triggers

Telegram alert is sent automatically when:
- Batch stopped (Chapter 4)
- Repeated failure breaker triggered (Chapter 5)
- Containment entered (Chapter 10)
- Per-round completion (normal exit)
- Human authorization required

### 11.4 Telegram Message Format

All Telegram messages must follow this structure:
```
[HH:MM:SS] {round_id} | {status} | {formal_status_code}
{free_text_summary}
{if blocked} BLOCKERS: {blocker_list}
{if blocked} FAILURE_POINT: {failure_point}
NEXT: {next_action}
```

### 11.5 Missing Telegram Report

Missing a Telegram report is an **informational gap** (not BLOCKED), but must be logged and escalated.

---

## CHAPTER 12: OpenAI API / Telegram API Failure / Timeout / Message Mismatch — Fail-Closed Rules

### 12.1 OpenAI API Failure

When OpenAI API returns an error:
- [ ] Batch execution stops immediately
- [ ] No silent continuation in reduced-capability mode
- [ ] Telegram alert sent: "OpenAI API error: {error_message}"
- [ ] Evidence preserved: full API request/response context (excluding credential values)
- [ ] Await human decision: retry, abort, or rollback

### 12.2 OpenAI API Timeout

When OpenAI API request times out:
- [ ] Batch execution stops immediately
- [ ] Telegram alert: "OpenAI API timeout: {timeout_duration}s"
- [ ] Await human decision

### 12.3 Telegram API Failure

When Telegram bot cannot send or receive messages:
- [ ] Batch execution stops immediately
- [ ] OpenCode agent does NOT continue autonomously
- [ ] Error logged to evidence
- [ ] Await human decision

### 12.4 Message Mismatch (OpenCode ↔ Telegram)

When expected Telegram response does not match actual response:
- [ ] Batch execution stops immediately
- [ ] Telegram alert: "Message mismatch: expected={expected}, actual={actual}"
- [ ] Await human decision

### 12.5 Validator Script Failure

When any validator script (check_branch_workflow.py, etc.) returns non-zero exit code:
- [ ] Batch stops immediately
- [ ] Telegram alert with validator output
- [ ] Await human decision

### 12.6 No Passive Mode Fallback

**FAIL-CLOSED**: There is no "passive mode" or "reduced-capability mode" for API auto-mode. When any failure occurs, the batch stops and awaits human decision. No automatic degradation without human authorization.

### 12.7 Timeout for Human Decision

If human does not respond within a defined timeout:
- Batch remains stopped (no auto-resume)
- Telegram reminder sent after timeout
- Await human indefinitely until explicit authorization

---

## MECHANICAL GUARDS (15 Required Guards)

These 15 mechanical guards are **enforceable by validator scripts** and result in BLOCKED status if violated:

| # | Guard Name | Implementation | Fail Condition |
|---|-----------|----------------|----------------|
| MG-01 | reply_id / round_id completeness | Every RETURN_TO_CHATGPT must have both round_id and reply_id | Missing either field = BLOCKED |
| MG-02 | RETURN_TO_CHATGPT formal body completeness | All fields required for task_type must be present | Missing required field = BLOCKED |
| MG-03 | formal_status_code validity | Must be "manual_review_completed" or "blocked" | Any other value = BLOCKED |
| MG-04 | candidate branch existence | work/{round_id}-candidate must exist with at least one commit | Not found = BLOCKED |
| MG-05 | candidate commit parent check | Candidate commit must have canonical HEAD as ancestor | No ancestor relationship = BLOCKED |
| MG-06 | forbidden file diff check | server.py, tests/, master, index.js, config.json, run_opencode_loop.ps1, .githooks/* must not have diff from canonical | Any diff = BLOCKED |
| MG-07 | canonical direct commit detection | check_branch_workflow.py detects "DIRECT_COMMIT_ON_CANONICAL_BLOCKED" | Detected = BLOCKED |
| MG-08 | merge post-commit extra block | No commits created after merge commit on canonical | Extra commits = BLOCKED |
| MG-09 | batch stop on first BLOCKED | Validator returning non-zero = batch stops; cannot continue | Not stopped = governance violation |
| MG-10 | batch rollback / containment trigger | STOP_NOW.flag recreation on repeated failure (3x) | Not triggered = governance violation |
| MG-11 | Telegram message alignment check | Expected vs actual Telegram response comparison | Mismatch = BLOCKED |
| MG-12 | OpenAI API error propagation | API error/timeout = batch stop; no silent continuation | Silent continuation = BLOCKED |
| MG-13 | no-verify prohibition | --no-verify on any git operation = BLOCKED | Detected = BLOCKED |
| MG-14 | evidence package real-work check | validate_evidence.py confirms "not packaging-only" | Packaging-only = BLOCKED |
| MG-15 | manifest schema validation | validate_round.py must pass for all manifests | Invalid schema = BLOCKED |

---

## APPLICABILITY SUMMARY

| Scope | Covered by This Law? |
|-------|----------------------|
| API-based auto-mode governance chain (OpenAI ↔ OpenCode ↔ Telegram) | **YES** |
| OpenCode agent round execution | **YES** |
| Phase 2 batch execution (R017–R048) | **YES** |
| R017 (trading broker secrets) | NO — separate round-specific law |
| Phase 2 per-round implementation rules | NO — separate round-specific laws (03法典) |
| Phase 1 (R001–R016) | NO — already closed |
| Lane release authorization | NO — separate authorization chain |
| Auto-mode release authorization | NO — separate authorization chain |

---

## VERSION AND STATUS

- **Version**: 1.0
- **Status**: ACTIVE
- **Effective Since**: Phase 2 hygiene alignment (canonical commit c980ef7)
- **Auto-mode Authorization**: NOT YET AUTHORIZED — this law governs auto-mode but auto-mode execution itself requires separate explicit human authorization
- **Phase 2 Entry**: NOT YET AUTHORIZED — requires separate explicit human authorization for R017

---

*Governance meta-law for Phase 2 API-based auto-mode batch execution.*
*Does not replace per-round implementation laws or R017 secrets management.*