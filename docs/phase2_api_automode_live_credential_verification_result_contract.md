# Phase 2 API Auto-Mode Live Credential Verification Result Contract

## Live Credential Verification Result Governance

**Document Version:** 1.0
**Status:** CANDIDATE - requires merge authorization
**Scope:** Live credential verification result schema and governance (NOT execution)
**Parent Law:** Phase 2 Batch Review Law (docs/phase2_batch_review_law.md)
**Governance Chain:** Phase 2 API Auto-Mode Governance Chain (docs/phase2_api_automode_governance_chain.md)

---

## IMPORTANT — SCOPE BOUNDARY

This document defines the **live credential verification result contract** for API-based auto-mode. It is NOT:
- Live credential verification execution
- OpenAI API calls or Telegram bot calls
- Execution authorization or execution
- R017 secrets management
- Phase 2 entry execution
- Trading runtime activation

This document DOES:
- Define live verification result schema
- Define required result fields
- Define allowed result states
- Define TTL/freshness rules
- Define fail-closed conditions
- Define secret masking/redaction rules
- Define verification result vs execution authorization boundary

**This document does NOT store real credentials or execute verification.**

---

## CHAPTER 1: Live Verification Result Schema

### 1.1 OpenAI Live Verification Result

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| provider | string | YES | "openai" |
| verification_target | string | YES | "api_key\|organization\|project" |
| timestamp | ISO8601 | YES | When verification was performed |
| correlation_key | string | YES | Links to authorization round |
| environment | string | YES | "production\|staging\|test" |
| result_status | enum | YES | pass / fail / stale / unknown / revoked |
| verifier_identity | string | YES | Who performed verification |
| ttl_seconds | integer | YES | Time-to-live for this result |
| expiry_timestamp | ISO8601 | YES | When this result expires |

### 1.2 Telegram Live Verification Result

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| provider | string | YES | "telegram" |
| verification_target | string | YES | "bot_token\|chat_id\|user_id" |
| timestamp | ISO8601 | YES | When verification was performed |
| correlation_key | string | YES | Links to authorization round |
| environment | string | YES | "production\|staging\|test" |
| result_status | enum | YES | pass / fail / stale / unknown / revoked |
| verifier_identity | string | YES | Who performed verification |
| ttl_seconds | integer | YES | Time-to-live for this result |
| expiry_timestamp | ISO8601 | YES | When this result expires |

---

## CHAPTER 2: Allowed Result States

### 2.1 Result State Definitions

| State | Meaning | Execution Allowed |
|-------|---------|-------------------|
| **pass** | Credentials valid and active | YES (if execution authorized) |
| **fail** | Credentials invalid or rejected | NO |
| **stale** | Result expired beyond TTL | NO |
| **unknown** | Verification not performed | NO |
| **revoked** | Credentials explicitly revoked | NO |

### 2.2 State Transitions

```
unknown -> pass (successful verification)
unknown -> fail (failed verification)
pass -> stale (TTL expired)
pass -> revoked (explicit revocation)
fail -> pass (re-verification successful)
stale -> pass (re-verification successful)
revoked -> pass (re-instatement, requires human authorization)
```

---

## CHAPTER 3: TTL / Freshness Rules

### 3.1 Default TTL Values

| Verification Type | Default TTL | Max TTL |
|------------------|-------------|---------|
| OpenAI API key | 3600 seconds (1 hour) | 86400 seconds (24 hours) |
| Telegram bot token | 3600 seconds (1 hour) | 86400 seconds (24 hours) |

### 3.2 Freshness Check

Before execution:
1. Check `expiry_timestamp`
2. If expired -> state = stale
3. If within TTL -> state remains pass
4. If no result exists -> state = unknown

### 3.3 Re-Verification Trigger

| Trigger | Action |
|---------|--------|
| TTL expired | Re-verify credentials |
| Execution failure | Re-verify credentials |
| Human request | Re-verify credentials |
| Credential change | Re-verify credentials |

---

## CHAPTER 4: Fail-Closed Rules

### 4.1 Missing Result

If verification result does not exist:
- State: unknown
- Execution: BLOCKED
- Action: Require verification before execution

### 4.2 Stale Result

If verification result expired:
- State: stale
- Execution: BLOCKED
- Action: Re-verify credentials

### 4.3 Revoked Result

If verification result revoked:
- State: revoked
- Execution: BLOCKED
- Action: Require human authorization to re-instate

### 4.4 Failed Result

If verification result failed:
- State: fail
- Execution: BLOCKED
- Action: Fix credentials, re-verify

---

## CHAPTER 5: Secret Masking / Redaction Rules

### 5.1 NO Plaintext Secrets

This contract NEVER stores:
- Real API keys
- Real bot tokens
- Real chat IDs
- Real user IDs

### 5.2 Result Redaction

Verification results must mask all credential values:

| Field | Masked Format |
|-------|---------------|
| api_key | sk-...REDACTED |
| bot_token | 1234567890:...REDACTED |
| chat_id | -0000000000:REDACTED |

### 5.3 Log Redaction

All logs must redact credential values:
- DO NOT log actual credentials
- DO NOT include credentials in RETURN_TO_CHATGPT
- DO NOT commit credentials to repository

---

## CHAPTER 6: Verification Result vs Execution Authorization Boundary

### 6.1 Verification Result Phase

Purpose: Record result of credential verification
- Does NOT authorize execution
- Does NOT execute API calls
- Does NOT open connections

### 6.2 Execution Authorization Phase

Purpose: Authorize actual execution
- Requires verification result = pass
- Requires execution_authorized = true
- Allows external API calls

### 6.3 Clear Boundary

```
Verification Result (this contract) -> separate from Execution Authorization
- Verification: records credential validity
- Execution: actual API calls
```

---

## CHAPTER 7: Rollback / Invalidation Rules

### 7.1 Credential Change Rollback

If credentials change:
1. Invalidate existing verification results
2. Set state to unknown
3. Block execution until re-verification
4. Notify human authority

### 7.2 Verification Failure Rollback

If re-verification fails:
1. Set state to fail
2. Block execution
3. Log failure reason
4. Notify human authority

### 7.3 Explicit Revocation

Human authority can revoke verification results:
1. Set state to revoked
2. Block execution
3. Require re-authorization to re-instate

---

## CHAPTER 8: Explicit Non-Authorization

### 8.1 This Contract Does NOT Authorize

| Item | Status |
|------|-------|
| Live credential verification execution | NOT AUTHORIZED |
| OpenAI API calls | NOT AUTHORIZED |
| Telegram bot execution | NOT AUTHORIZED |
| Execution authorization | NOT YET |
| R017 secrets management | Separate round |
| Phase 2 entry | Separate track |

### 8.2 Prerequisites

Before execution can proceed:
- Live verification result = pass
- Result within TTL
- Execution authorized (separate decision)
- All other blockers resolved

---

## VERSION AND STATUS

- **Version**: 1.0 CANDIDATE
- **Status**: Requires merge authorization
- **Requires merge**: YES
- **Requires push**: YES
- **Verification result contract**: YES
- **Execution authorized**: NOT YET

---

*Live credential verification result contract for Phase 2 API auto-mode.*
*Defines result schema, states, TTL rules, and fail-closed conditions.*
*Does NOT authorize execution - only defines result governance.*