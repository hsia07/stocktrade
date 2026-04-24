# Phase 2 API Auto-Mode External Dependency Verification Contract

## Credential Verification Governance

**Document Version:** 1.0
**Status:** CANDIDATE - requires merge authorization
**Scope:** OpenAI API and Telegram credential verification (NOT execution)
**Parent Law:** Phase 2 Batch Review Law (docs/phase2_batch_review_law.md)
**Governance Chain:** Phase 2 API Auto-Mode Governance Chain (docs/phase2_api_automode_governance_chain.md)

---

## IMPORTANT — SCOPE BOUNDARY

This document defines the **external dependency verification contract** for API-based auto-mode. It is NOT:
- Execution authorization or execution
- OpenAI API calls or Telegram bot calls
- R017 secrets management
- Phase 2 entry execution
- Trading runtime activation

This document DOES:
- Define credential verification scope
- Define required verification fields
- Define fail-closed conditions for missing/invalid credentials
- Define secret masking/redaction rules
- Define verification failure rollback

**This document does NOT store real credentials.**

---

## CHAPTER 1: Verification Scope

### 1.1 OpenAI Credential Verification

| Field | Required | Verification |
|-------|----------|---------------|
| api_key | REDACTED | Verify format (sk-...), NOT actual validity |
| organization_id | OPTIONAL | Verify format (org-...), NOT actual validity |
| project_id | OPTIONAL | Verify format (proj-...), NOT actual validity |

### 1.2 Telegram Credential Verification

| Field | Required | Verification |
|-------|----------|---------------|
| bot_token | REDACTED | Verify format (digits:alpha), NOT actual validity |
| chat_id | REDACTED | Verify numeric format, NOT actual existence |
| user_id | OPTIONAL | Verify numeric format |

### 1.3 Verification NOT Included

This verification does NOT:
- Store actual API keys or bot tokens
- Validate credentials against live services
- Execute any API calls
- Access any trading systems

---

## CHAPTER 2: Verification Fail-Closed Conditions

### 2.1 Misssing Credential Fields

If required field is missing:
- Verification status: FAILED
- Failure reason: "missing_required_field"
- Execution blocked until resolution

### 2.2 Invalid Credential Format

If credential format is invalid:
- Verification status: FAILED
- Failure reason: "invalid_credential_format"
- Execution blocked until resolution

### 2.3 Credential Expiration

If credential appears expired:
- Verification status: FAILED
- Failure reason: "credential_expired"
- Execution blocked until resolution

### 2.4 Verification Success

If all credentials verified:
- Verification status: PASSED
- Verification timestamp recorded
- Execution can proceed (if authorization granted)

---

## CHAPTER 3: Secret Masking Rules

### 3.1 REDACTED Masking

All credential values must be REDACTED in logs and evidence:

| Field | Masked Format |
|-------|---------------|
| api_key | sk-...REDACTED |
| bot_token | 1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqr...REDACTED |
| chat_id | -0000000000:REDACTED |
| user_id | 000000000:REDACTED |

### 3.2 Verification Evidence

Verification results must mask all credential values:
- DO NOT log actual credentials
- DO NOT include credentials in RETURN_TO_CHATGPT
- DO NOT commit credentials to repository

### 3.3 Redacted Examples

OpenAI Verification Example:
```json
{
  "verification_status": "PASSED",
  "verification_timestamp": "2026-04-24T14:00:00Z",
  "openai_credentials": {
    "api_key": "sk-...REDACTED",
    "organization_id": "org-...REDACTED"
  }
}
```

Telegram Verification Example:
```json
{
  "verification_status": "PASSED",
  "verification_timestamp": "2026-04-24T14:00:00Z",
  "telegram_credentials": {
    "bot_token": "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqr...REDACTED",
    "chat_id": "-0000000000:REDACTED"
  }
}
```

---

## CHAPTER 4: Verification Failure Handling

### 4.1 Verification Failure Response

On verification failure:
- Status returned: "failed"
- Formal status code: "verification_failed"
- Failure reason captured
- Execution prohibited

### 4.2 Rollback on Verification Failure

If verification fails:
- Lock state remains UNLOCKED
- activation_authorized remains true
- execution_authorized remains false
- Human notified of failure

### 4.3 Containment on Repeated Failure

If verification fails 3 times:
- Verification disabled until human review
- Lock state can be reverted to LOCKED
- Containment triggered per governance rules

---

## CHAPTER 5: Verification vs Execution Authorization Boundary

### 5.1 Verification Phase

Purpose: Verify credential format and presence
- Does NOT validate credentials against live services
- Does NOT execute API calls
- Does NOT open connections

### 5.2 Execution Authorization Phase

Purpose: Authorize actual execution
- Requires verification PASSED
- Requires separate execution_authorized = true
- Allows external API calls

### 5.3 Clear Boundary

Verification (this contract) -> separate from Execution Authorization
- Verification: format check
- Execution: actual API calls

---

## CHAPTER 6: Explicit Non-Authorization

### 6.1 This Contract Does NOT Authorize

| Item | Status |
|------|-------|
| OpenAI API calls | NOT AUTHORIZED |
| Telegram bot execution | NOT AUTHORIZED |
| Execution authorization | NOT YET |
| R017 secrets management | Separate round |
| Phase 2 entry | Separate track |

### 6.2 Prerequisites

Before execution can proceed:
- Verification PASSED (format check)
- Execution authorized (separate decision)
- All other blockers resolved

---

## VERSION AND STATUS

- **Version**: 1.0 CANDIDATE
- **Status**: Requires merge authorization
- **Requires merge**: YES
- **Requires push**: YES
- **Verification authorized**: YES (format check only)
- **Execution authorized**: NOT YET

---

*External dependency verification contract for Phase 2 API auto-mode.*
*Defines credential verification scope, fail-closed conditions, and secret masking rules.*
*Does NOT authorize execution - only verifies credential format.*