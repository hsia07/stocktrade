# Phase 2 API Auto-Mode Governance Chain
## OpenAI API ↔ OpenCode ↔ Telegram Bot Orchestration Governance

**Document Version:** 1.0
**Status:** DRAFT CANDIDATE - requires merge authorization
**Scope:** API-based auto-mode governance chain (OpenAI API ↔ OpenCode ↔ Telegram bot)
**Parent Law:** Phase 2 Batch Review Law (docs/phase2_batch_review_law.md)
**Applicable Phases:** Phase 2 (R017–R048) and all subsequent phases

---

## IMPORTANT — SCOPE BOUNDARY

This document defines the governance chain for **API-based auto-mode orchestration** (OpenAI API ↔ OpenCode ↔ Telegram bot loop).

**This document does NOT cover:**
- R017 (秘密與金鑰管理 / Trading broker credentials) — separate round-specific law
- Phase 2 per-round implementation (R017–R048) — each governed by its own law
- API auto-mode activation itself — requires separate authorization
- Phase 2 entry (R017) — requires separate authorization

**This document does NOT replace:**
- Phase 2 Batch Review Law (governance meta-law)
- Any round-specific implementation rules (03_161輪逐輪施行細則法典)
- R017 secrets management requirements

---

## CHAPTER 1: Role Definitions

### 1.1 Orchestration Roles

| Role | Responsibility | Authority |
|------|-------------|----------|
| **Telegram User** | Sends trigger commands, receives notifications, human approvals | Triggers tasks, approves human decisions |
| **Telegram Bot** | Receives commands, sends notifications, relays human approvals | Message relay only - no autonomous decisions |
| **OpenAI API** | Generates task suggestions, analyzes output, provides LLM reasoning | Input/output processing only - no execution |
| **OpenCode (Agent)** | Executes tasks, produces RETURN_TO_CHATGPT, validates | Primary execution under governance rules |
| **Human Authority** | Explicit authorization for merge/push/auto-mode/start | Highest authority |

### 1.2 Orchestration Flow

```
Telegram User Command
    ↓
Telegram Bot Relay (store message)
    ↓
OpenCode Task Dispatch (parse round_id, task_type)
    ↓
OpenAI API (optional: generate/suggest)
    ↓
OpenCode Execution
    ↓
RETURN_TO_CHATGPT Production
    ↓
Telegram Bot Report (status, blockers, next_action)
    ↓
Human Authority Decision
```

---

## CHAPTER 2: Entry / Exit / Authorization Events

### 2.1 Entry Events

| Event | Trigger | Required Verification |
|-------|---------|----------------------|
| **round_start** | Telegram command with round_id | round_id in current_round.yaml |
| **task_dispatch** | OpenCode receives task | task_type must be valid |
| **merge_trigger** | Human approval for merge | merge authorization evidence |
| **push_trigger** | Human approval for push | push authorization evidence |
| **auto_mode_trigger** | Human approval for auto-mode start | separate authorization required |

### 2.2 Exit Events

| Event | Condition |
|-------|----------|
| **normal_exit** | RETURN_TO_CHATGPT complete, validators pass |
| **blocked_exit** | Validator fails, failure_point captured |
| **emergency_exit** | Repeated failure breaker triggered |

### 2.3 Authorization Events

- **merge_authorization**: Explicit human approval required per batch review law
- **push_authorization**: Explicit human approval required per batch review law
- **auto_mode_authorization**: NOT YET AUTHORIZED - requires separate approval
- **phase2_entry_authorization**: NOT YET AUTHORIZED - requires separate approval

---

## CHAPTER 3: Round ID / Task Type / Reply ID Alignment Rules

### 3.1 Required Field Mapping

Every Telegram → OpenCode → RETURN_TO_CHATGPT cycle must maintain:

```
Telegram Message:
  round_id: "PHASE2-BATCH-REVIEW-LAW"
  task_type: "phase2_batch_review_law_candidate_draft"

↓
OpenCode Dispatch:
  round_id: MUST match Telegram
  task_type: MUST match Telegram
  reply_id: "phase2-batch-review-law-XXX"

↓
RETURN_TO_CHATGPT:
  round_id: MUST match dispatch
  task_type: MUST match dispatch
  reply_id: MUST match dispatch
  formal_status_code: "manual_review_completed" or "blocked"
```

### 3.2 Alignment Guards

| Guard | Check | Fail Condition |
|-------|-------|-------------|
| **round_id_match** | Telegram round_id = Dispatch round_id = RETURN round_id | Mismatch = BLOCKED |
| **task_type_match** | Telegram task_type = Dispatch task_type = RETURN task_type | Mismatch = BLOCKED |
| **reply_id_presence** | reply_id in RETURN_TO_CHATGPT | Missing = BLOCKED |
| **formal_status_code_valid** | Only "manual_review_completed" or "blocked" | Invalid = BLOCKED |

---

## CHAPTER 4: Fail-Closed Rules

### 4.1 OpenAI API Failures

| Failure | Action |
|---------|--------|
| **API timeout** | Batch stop → Telegram alert → await human |
| **API error** | Batch stop → Telegram alert → await human |
| **Malformed response** | Batch stop → Telegram alert → await human |
| **Retry failure** | Do NOT auto-retry beyond 1x → containment |

### 4.2 Telegram Failures

| Failure | Action |
|---------|--------|
| **Send failure** | Batch stop → await human |
| **Reply timeout** | Batch stop → await human |
| **Wrong reply** | Batch stop → await human |
| **Duplicate reply** | Batch stop → containment → await human |

### 4.3 Message Mismatch Rules

If Telegram response differs from expected:
- **Mismatch detected**: immediate batch stop
- **Log failure_point**: record exact mismatch details
- **Telegram alert**: send containment notification
- **Await human**: no auto-resume

---

## CHAPTER 5: Human Approval Gate

### 5.1 Human-Gated Actions

| Action | Requires Human Approval |
|--------|-----------------|
| **merge** | YES - explicit approval |
| **push** | YES - explicit approval |
| **lane_release** | YES - explicit approval |
| **auto_mode_start** | YES - explicit approval (NOT YET AUTHORIZED) |
| **phase2_entry** | YES - explicit approval (NOT YET AUTHORIZED) |
| **rollback** | YES - explicit approval |
| **containment_override** | YES - explicit approval |

### 5.2 OpenCode Executable Boundaries

OpenCode CAN execute without human approval:
- **candidate_draft**: create candidate files, run validators
- **decision_audit**: analyze and report
- **validation_run**: execute validators

OpenCode CANNOT execute without human approval:
- **merge**: requires merge_authorization
- **push**: requires push_authorization
- **auto_mode_start**: NOT AUTHORIZED
- **phase2_entry**: NOT AUTHORIZED

---

## CHAPTER 6: Batch Stop / Containment Integration

### 6.1 Batch Stop Triggers

Per Phase 2 Batch Review Law Chapter 4:
- Any validator FAIL → batch stops
- Any BLOCKED status → batch stops
- Forbidden file modified → batch stops
- Return TO_CHATGPT invalid → batch stops

### 6.2 Containment Triggers

Per Phase 2 Batch Review Law Chapter 10:
- Repeated failure (same round, 3x) → containment
- API failure not recovered → containment
- Telegram failure not recovered → containment

### 6.3 Chain Relationship

- **Governance Meta-Law**: Phase 2 Batch Review Law (parent)
- **Governance Chain**: This document (child - defines orchestration)
- **Execution**: Both required for API auto-mode
- **Authorization**: Both required but separate

---

## CHAPTER 7: Audit Trail / Traceability

### 7.1 Required Traceability

| Event | Record |
|-------|--------|
| **Telegram received** | timestamp, round_id, task_type, raw message |
| **Dispatched** | round_id, task_type, reply_id, timestamp |
| **Execution** | commands executed, stdout, stderr |
| **RETURN_TO_CHATGPT** | round_id, task_type, reply_id, status, blockers |
| **Telegram report** | timestamp, round_id, status, failure_point (if any) |

### 7.2 Idempotency Rules

- **Same Telegram command twice**: Same reply_id, same output
- **Retry within 5 minutes**: SAME execution + SAME return
- **Different round_id**: New execution, new return
- **Idempotency key**: round_id + task_type + timestamp(5min window)

### 7.3 Deduplication

- **Hash**: SHA256 of (round_id + task_type + timestamp truncated to minute)
- **Store**: In Telegram message context (not to any persistent store)
- **Detect**: If within 5 minutes, return cached result

---

## CHAPTER 8: Non-Authorization Declarations

### 8.1 Explicit Non-Authorization

| Item | Status |
|-----|-------|
| **API auto-mode activation** | NOT AUTHORIZED - requires separate approval |
| **Phase 2 entry (R017)** | NOT AUTHORIZED - requires separate approval |
| **R017 construction** | Separate round law only |
| **API auto-mode execution** | NOT AUTHORIZED - requires separate approval |

### 8.2 Chain Dependency

This governance chain DEPENDS on:
- Phase 2 Batch Review Law (docs/phase2_batch_review_law.md)
- Validation scripts (check_branch_workflow.py, etc.)

This governance chain DOES NOT REPLACE:
- Phase 2 Batch Review Law
- Any round-specific laws
- R017 secrets management

---

## VERSION AND STATUS

- **Version**: 1.0 DRAFT CANDIDATE
- **Status**: CANDIDATE - requires merge authorization
- **Requires merge**: YES - via Phase 2 Batch Review Law flow
- **Requires push**: YES - via Phase 2 Batch Review Law flow
- **Auto-mode authorization**: NOT YET AUTHORIZED
- **Phase 2 entry**: NOT YET AUTHORIZED

---

*Governance chain document for Phase 2 API-based auto-mode orchestration.*
*Complements Phase 2 Batch Review Law, does not replace it.*
*Does not authorize auto-mode execution, only defines the governance chain.*