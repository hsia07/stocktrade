# Phase 2 API Auto-Mode Activation Contract

## OpenAI API ↔ OpenCode ↔ Telegram Bot Activation Governance

**Document Version:** 1.0
**Status:** CANDIDATE - requires merge authorization
**Scope:** API-based auto-mode activation contract (not execution)
**Parent Law:** Phase 2 Batch Review Law (docs/phase2_batch_review_law.md)
**Governance Chain:** Phase 2 API Auto-Mode Governance Chain (docs/phase2_api_automode_governance_chain.md)

---

## IMPORTANT — SCOPE BOUNDARY

This document defines the **activation contract** for API-based auto-mode. It is NOT:
- API auto-mode execution (requires separate activation authorization)
- R017 secrets management
- Phase 2 entry execution
- Telegram/OpenAI integration implementation

This document DOES:
- Define activation preconditions
- Define authorization events and lock conditions
- Define role responsibilities before/after activation
- Define fail-closed conditions
- Define rollback and containment conditions
- Define dry-run/no-op mode boundaries

---

## CHAPTER 1: Activation Preconditions

### 1.1 Governance Preconditions

| Precondition | Status | Verification |
|------------|--------|-------------|
| Phase 2 Batch Review Law | ON REMOTE | docs/phase2_batch_review_law.md exists |
| Phase 2 API Governance Chain | ON REMOTE | docs/phase2_api_automode_governance_chain.md exists |
| Evidence Reconciliation | COMPLETE | manifests/phase2_api_automode_governance_chain_evidence_reconciliation.yaml |
| Lane Status | RELEASED | automation/control/STOP_NOW.flag absent |

### 1.2 Runtime Preconditions

| Precondition | Status | Verification |
|------------|--------|-------------|
| env001 (FastAPI/Pydantic) | BLOCKED | Known environment debt |
| Telegram Message Contract | REQUIRED | Fixture exists (docs/phase2_api_automode_message_contract_fixture.md) |
| Authorization Lock | REQUIRED | automation/control/AUTO_MODE_ACTIVATION_LOCK exists |

### 1.3 Activation NOT Authorized Until

- Explicit human authorization via AUTO_MODE_ACTIVATION_LOCK
- Activation contract merged to canonical
- Activation manifest merged to manifests/
- All 4 governance validators pass

---

## CHAPTER 2: Authorization Events and Lock Conditions

### 2.1 Authorization Events

| Event | Trigger | Required Verification |
|-------|---------|----------------------|
| **lock_creation** | Create AUTO_MODE_ACTIVATION_LOCK | Human explicit approval |
| **lock_activation** | Authorize activation | lock file contains authorization timestamp |
| **lock_invalidation** | Delete/disable lock | Human explicit approval |
| **lock_extension** | Extend activation period | Human explicit approval |

### 2.2 Lock Conditions

**AUTO_MODE_ACTIVATION_LOCK structure:**
```json
{
  "lock_id": "AUTO_MODE_ACTIVATION_LOCK",
  "status": "LOCKED|UNLOCKED|INVALIDATED",
  "created_at": "ISO8601 timestamp",
  "authorized_by": "human authority identifier",
  "activation_authorized": false,
  "valid_until": "ISO8601 timestamp or null",
  "reason": "activation contract establishment",
  "dependencies": {
    "phase2_batch_review_law": "on_remote",
    "governance_chain": "on_remote",
    "evidence_reconciliation": "complete"
  },
  "blockers": {
    "r017_not_authorized": true,
    "phase2_entry_not_authorized": true,
    "env001_present": true
  }
}
```

**Lock State Rules:**
- LOCKED: Activation not authorized
- UNLOCKED: Activation authorized by human
- INVALIDATED: Activation explicitly denied or expired

### 2.3 Authorization Chain

```
1. Create activation contract (THIS DOCUMENT)
2. Create activation manifest (manifests/phase2_api_automode_activation.yaml)
3. Create AUTO_MODE_ACTIVATION_LOCK (LOCKED state)
4. Merge to canonical (evidence package required)
5. Human authorizes UNLOCKED state
6. Activation permitted (NOT execution, only authorization)
```

---

## CHAPTER 3: Role Responsibilities

### 3.1 Pre-Activation Responsibilities

| Role | Responsibility |
|------|-------------|
| **Telegram User** | Send commands, receive reports |
| **Telegram Bot** | Relay messages, store state |
| **OpenAI API** | LLM processing (if configured) |
| **OpenCode** | Execute governance tasks, produce evidence |
| **Human Authority** | Grant/deny activation authorization |

### 3.2 Post-Activation Responsibilities

| Role | Responsibility |
|------|-------------|
| **Telegram User** | Send trigger commands, approve actions |
| **Telegram Bot** | Relay messages, dispatch to OpenCode |
| **OpenAI API** | Process requests, generate responses |
| **OpenCode** | Execute tasks under governance rules |
| **Human Authority** | Monitor, intervene if blocked |

### 3.3 Post-Activation Boundaries

**OpenCode boundaries after activation:**
- Must respect AUTO_MODE_ACTIVATION_LOCK state
- Must produce RETURN_TO_CHATGPT with lock state
- Must validate activation status before execution
- Must fail-closed if lock is LOCKED or INVALIDATED

---

## CHAPTER 4: Fail-Closed Conditions

### 4.1 Activation Fail-Closed Conditions

| Condition | Action |
|-----------|-------|
| Lock state = LOCKED | Block all auto-mode execution |
| Lock state = INVALIDATED | Block all auto-mode execution |
| Lock does not exist | Block all auto-mode execution |
| Lock expired | Block all auto-mode execution |
| env001 blocks execution | Block auto-mode execution |

### 4.2 Message Fail-Closed Conditions

| Condition | Action |
|-----------|-------|
| Missing required field | Reject message, log failure_point |
| Invalid correlation key | Reject message, log failure_point |
| Timeout exceeded | Reject message, log failure_point |
| Duplicate message | Return cached response (idempotent) |
| Mismatched round_id | Reject message, propose new round_id |

### 4.3 Execution Fail-Closed Conditions

| Condition | Action |
|-----------|-------|
| No AUTO_MODE_ACTIVATION_LOCK | Block execution |
| Lock state != UNLOCKED | Block execution |
| Validator fails | Block execution |
| Unauthorized state transition | Block execution |

---

## CHAPTER 5: Timeout / Retry / Mismatch Handling

### 5.1 Timeout Rules

| Timeout Type | Duration | Action |
|-------------|---------|--------|
| Message dispatch | 30 seconds | Retry once, then fail |
| Command execution | 300 seconds (5 min) | Retry once, then fail |
| Lock response | 60 seconds | Fail-closed |
| Human approval | 3600 seconds (1 hr) | Timeout → reject |

### 5.2 Retry Rules

- **Same command twice**: Same reply_id, same output (idempotent)
- **Retry within 5 minutes**: SAME execution + SAME return
- **Different round_id**: New execution, new return
- **Retry after timeout**: New execution, new reply_id

### 5.3 Mismatch Handling

| Mismatch Type | Handling |
|---------------|----------|
| round_id mismatch | Reject, propose correct round_id |
| task_type mismatch | Reject, propose correct task_type |
| required_field missing | Reject, list missing fields |
| unauthorized field | Reject, log security event |

---

## CHAPTER 6: Rollback and Containment Conditions

### 6.1 Rollback Conditions

| Trigger | Rollback Action |
|---------|--------------|
| Human invalidates lock | Set lock state to INVALIDATED |
| Lock expires | Set lock state to LOCKED |
| Validator failure | Block execution, require human review |
| Repeated failure (3x) | Containment triggered |

### 6.2 Containment Conditions

| Trigger | Containment Action |
|---------|-----------------|
| Repeated failure (same round, 3x) | Auto-mode blocked until human review |
| API failure not recovered | Containment until resolution |
| Telegram failure not recovered | Containment until resolution |
| Security event detected | Containment until human review |

### 6.3 Rollback Authorization

- **Who can rollback**: Human Authority only
- **Who can invalidate**: Human Authority only
- **Who can contain**: Automated (per fail-closed conditions)

---

## CHAPTER 7: Dry-Run / No-Op Mode

### 7.1 Dry-Run Mode

**Dry-run mode** allows message processing WITHOUT actual execution.

**Dry-run allowed WITHOUT authorization:**
- YES: Message contract validation
- YES: Required field checking
- YES: Correlation key validation
- YES: Timeout simulation
- NO: Actual command execution
- NO: API calls to external services
- NO: State mutations outside message relay

### 7.2 No-Op Mode

**No-op mode** allows activation authorization WITHOUT execution.

**No-op allowed WITHOUT authorization:**
- YES: Lock state transitions
- YES: Authorization event logging
- YES: Message shape validation
- NO: Actual auto-mode execution
- NO: Command execution
- NO: External API calls

### 7.3 Dry-Run Authorization Boundaries

| Action | Authorization Required |
|--------|-------------------|
| Validate message shape | NO |
| Check required fields | NO |
| Simulate timeout | NO |
| Log attempted execution | NO |
| Execute actual command | YES (UNLOCKED) |
| Call external API | YES (UNLOCKED) |
| Mutate state | YES (UNLOCKED) |

---

## CHAPTER 8: Explicit Non-Authorization Declarations

### 8.1 Current Status

| Item | Status |
|------|-------|
| API auto-mode execution | NOT AUTHORIZED |
| Activation execution | NOT AUTHORIZED |
| Phase 2 entry (R017) | NOT AUTHORIZED |
| R017 construction | Separate round only |
| env001 remediation | Known debt |

### 8.2 Dependencies

This activation contract DEPENDS on:
- Phase 2 Batch Review Law (parent law)
- Phase 2 API Governance Chain (governance chain)
- Evidence reconciliation completion

This activation contract DOES NOT REPLACE:
- Phase 2 Batch Review Law
- Phase 2 API Governance Chain
- R017 secrets management
- Any round-specific laws

---

## VERSION AND STATUS

- **Version**: 1.0 CANDIDATE
- **Status**: Requires merge authorization
- **Requires merge**: YES
- **Requires push**: YES
- **Activation authorized**: NOT YET — requires separate human authorization

---

*Activation contract for Phase 2 API-based auto-mode.*
*Defines activation preconditions, authorization events, and fail-closed conditions.*
*Does not authorize execution — only establishes the contract framework.*