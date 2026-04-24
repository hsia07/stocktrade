# Phase 2 API Auto-Mode Message Contract Fixture

## OpenAI API ↔ OpenCode ↔ Telegram Message Contract

**Document Version:** 1.0
**Status:** CANDIDATE - for fixture/validation only
**Scope:** Message shape, required fields, correlation keys, timeout behavior
**Purpose:** Validate message contract without actual execution

---

## IMPORTANT — SCOPE BOUNDARY

This document defines the **message contract fixture** for API-based auto-mode:
- Message shape and required fields
- Correlation keys
- Timeout behavior
- Mismatch fail-closed conditions
- **NOT for actual execution**
- **NOT for external API calls**
- **NO real secrets/API keys**

This fixture is for validation and dry-run purposes only.

---

## CHAPTER 1: Message Shapes

### 1.1 Telegram → OpenCode Message

**Trigger Message (user sends to bot):**
```json
{
  "message_id": "uuid_v4",
  "timestamp": "ISO8601",
  "source": "telegram",
  "user_id": "telegram_user_id",
  "chat_id": "telegram_chat_id",
  "round_id": "PHASE2-API-AUTOMODE-ACTIVATION-CONTRACT",
  "task_type": "api_automode_activation_contract_creation",
  "text": "Execute activation contract",
  "metadata": {
    "command": "/start_activation_contract"
  }
}
```

### 1.2 OpenCode → Telegram Message

**Response Message (OpenCode sends to bot):**
```json
{
  "reply_id": "phase2-api-automode-activation-contract-001",
  "timestamp": "ISO8601",
  "status": "completed|failed|blocked",
  "formal_status_code": "candidate_ready_awaiting_manual_review|blocked",
  "round_id": "PHASE2-API-AUTOMODE-ACTIVATION-CONTRACT",
  "task_type": "api_automode_activation_contract_creation",
  "correlation_key": {
    "original_message_id": "uuid_v4",
    "round_id": "PHASE2-API-AUTOMODE-ACTIVATION-CONTRACT"
  },
  "content": "RETURN_TO_CHATGPT payload",
  "metadata": {}
}
```

### 1.3 OpenCode → OpenAI API Message (if configured)

**Request Message:**
```json
{
  "request_id": "uuid_v4",
  "timestamp": "ISO8601",
  "source": "opencode",
  "target": "openai_api",
  "round_id": "PHASE2-API-AUTOMODE-ACTIVATION-CONTRACT",
  "model": "gpt-4o-mini",
  "messages": [
    {
      "role": "system",
      "content": "You are a governance agent..."
    },
    {
      "role": "user",
      "content": "Execute activation contract task"
    }
  ],
  "metadata": {
    "correlation_key": "uuid_v4",
    "timeout_seconds": 30
  }
}
```

---

## CHAPTER 2: Required Fields

### 2.1 Telegram → OpenCode Required Fields

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| message_id | UUID | YES | Must be valid UUID |
| timestamp | ISO8601 | YES | Must be valid timestamp |
| round_id | string | YES | Must match current_round.yaml |
| task_type | string | YES | Must be valid task_type |
| text | string | YES | Non-empty |
| correlation_key | object | YES | Must contain original_message_id and round_id |

### 2.2 OpenCode → Telegram Required Fields

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| reply_id | string | YES | Must be unique |
| timestamp | ISO8601 | YES | Must be valid timestamp |
| status | string | YES | Must be completed\|failed\|blocked |
| formal_status_code | string | YES | Must be valid code |
| round_id | string | YES | Must match request |
| correlation_key | object | YES | Must link to original message |

### 2.3 Fail-Closed on Missing Field

- Missing required field → Reject message
- Log failure_point: "missing_required_field: <field_name>"
- Do not proceed to execution

---

## CHAPTER 3: Correlation Keys

### 3.1 Correlation Key Structure

```json
{
  "correlation_key": {
    "original_message_id": "uuid_v4",
    "original_timestamp": "ISO8601",
    "round_id": "PHASE2-API-AUTOMODE-ACTIVATION-CONTRACT",
    "reply_to": "uuid_v4"
  }
}
```

### 3.2 Correlation Validation

- Round ID must match current_round.yaml
- Message ID must be unique or matching retry
- Timestamp must be within valid window (5 minutes)

### 3.3 Idempotency Rules

- Same message within 5 minutes → Same reply_id, same output
- Retry after 5 minutes → New execution, new reply_id
- Different round_id → New execution, new reply_id

---

## CHAPTER 4: Timeout Behavior

### 4.1 Timeout Types

| Timeout Type | Duration | Action |
|-------------|---------|--------|
| Message dispatch | 30 seconds | Retry once, then fail |
| Command execution | 300 seconds (5 min) | Retry once, then fail |
| Lock response | 60 seconds | Fail-closed |
| Human approval | 3600 seconds (1 hr) | Timeout → reject |

### 4.2 Timeout Handling

- **Timeout during message dispatch**: Retry once with exponential backoff
- **Timeout during execution**: Fail-closed, log failure_point
- **Timeout during lock check**: Fail-closed, block execution

### 4.3 Timeout Fail-Closed

If timeout occurs:
1. Log failure_point with timeout type and duration
2. Do not proceed to execution
3. Return failure response with appropriate status
4. Notify human if required

---

## CHAPTER 5: Mismatch Fail-Closed

### 5.1 Mismatch Types

| Mismatch Type | Handling |
|---------------|----------|
| round_id mismatch | Reject, propose correct round_id |
| task_type mismatch | Reject, propose correct task_type |
| required_field missing | Reject, list missing fields |
| unauthorized field | Reject, log security event |
| correlation_key invalid | Reject, request valid key |

### 5.2 Mismatch Response

```json
{
  "status": "blocked",
  "formal_status_code": "mismatch_detected",
  "failure_point": "round_id_mismatch",
  "expected": "PHASE2-API-AUTOMODE-ACTIVATION-CONTRACT",
  "received": "INVALID_ROUND_ID",
  "proposed_correction": "PHASE2-API-AUTOMODE-ACTIVATION-CONTRACT"
}
```

---

## CHAPTER 6: Dry-Run Validation

### 6.1 Dry-Run Allowed Without Execution

| Action | Allowed | Authorization Required |
|--------|---------|----------------------|
| Validate message shape | YES | NO |
| Check required fields | YES | NO |
| Validate correlation keys | YES | NO |
| Simulate timeout | YES | NO |
| Log message attempt | YES | NO |

### 6.2 Not Allowed Without Execution

| Action | Not Allowed | Authorization Required |
|--------|------------|----------------------|
| Execute actual command | NO | YES (UNLOCKED) |
| Call external API | NO | YES (UNLOCKED) |
| Mutate state | NO | YES (UNLOCKED) |
| Send to Telegram | NO | YES (UNLOCKED) |

---

## CHAPTER 7: Fixture Validation

### 7.1 Validation Script Usage

This fixture can be validated using:

```bash
python scripts/validation/validate_evidence.py \
  --manifest manifests/phase2_api_automode_activation.yaml \
  --repo-root .
```

### 7.2 Expected Validation Results

- validate_evidence.py: PASS (message contract fixture validates dry-run)
- check_forbidden_changes.py: PASS
- check_required_evidence.py: PASS
- check_branch_workflow.py: PASS

---

## CHAPTER 8: Explicit Non-Authorization

### 8.1 Fixture Status

This is a **fixture only**:
- **Not for actual execution**
- **Not for external API calls**
- **No real secrets/API keys**
- **For validation and dry-run purposes**

### 8.2 Non-Authorization Declarations

| Item | Status |
|------|-------|
| API auto-mode execution | NOT AUTHORIZED |
| External API calls | NOT AUTHORIZED |
| State mutations | NOT AUTHORIZED |
| Telegram messages | NOT AUTHORIZED (dry-run only) |

---

*Message contract fixture for Phase 2 API auto-mode.*
*Defines message shapes, required fields, correlation keys, and timeout behavior.*
*For validation and dry-run only — not for actual execution.*