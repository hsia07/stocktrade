# Phase 2 API Auto-Mode Live Verification Result Fixture

## Live Credential Verification Result Format

**Document Version:** 1.0
**Status:** CANDIDATE - fixture only, no real credentials
**Purpose:** Define live verification result format for API auto-mode

---

## IMPORTANT — NO REAL CREDENTIALS

This fixture defines the **format** for live verification results. It does NOT contain:
- Real OpenAI API keys
- Real Telegram bot tokens
- Real chat IDs or user IDs
- Real verification results

All values are **REDACTED** or **EXAMPLE FORMAT ONLY**.

---

## CHAPTER 1: OpenAI Live Verification Result

### 1.1 Result Format

```json
{
  "provider": "openai",
  "verification_target": "api_key",
  "timestamp": "2026-04-24T15:00:00Z",
  "correlation_key": "PHASE2-API-AUTOMODE-LIVE-CREDENTIAL-VERIFICATION-RESULT-CONTRACT",
  "environment": "production",
  "result_status": "pass",
  "verifier_identity": "human_authority",
  "ttl_seconds": 3600,
  "expiry_timestamp": "2026-04-24T16:00:00Z",
  "credentials_masked": true,
  "api_key": "sk-...REDACTED",
  "organization_id": "org-...REDACTED",
  "project_id": "proj-...REDACTED"
}
```

### 1.2 Result States

| State | Example |
|-------|---------|
| pass | Verification successful |
| fail | Verification failed |
| stale | Result expired |
| unknown | Not verified |
| revoked | Explicitly revoked |

---

## CHAPTER 2: Telegram Live Verification Result

### 2.1 Result Format

```json
{
  "provider": "telegram",
  "verification_target": "bot_token",
  "timestamp": "2026-04-24T15:00:00Z",
  "correlation_key": "PHASE2-API-AUTOMODE-LIVE-CREDENTIAL-VERIFICATION-RESULT-CONTRACT",
  "environment": "production",
  "result_status": "pass",
  "verifier_identity": "human_authority",
  "ttl_seconds": 3600,
  "expiry_timestamp": "2026-04-24T16:00:00Z",
  "credentials_masked": true,
  "bot_token": "1234567890:...REDACTED",
  "chat_id": "-0000000000:REDACTED",
  "user_id": "0000000000:REDACTED"
}
```

### 2.2 Result States

| State | Example |
|-------|---------|
| pass | Verification successful |
| fail | Verification failed |
| stale | Result expired |
| unknown | Not verified |
| revoked | Explicitly revoked |

---

## CHAPTER 3: Verification Result Response

### 3.1 Success Response

```json
{
  "verification_type": "openai|telegram",
  "status": "pass",
  "timestamp": "2026-04-24T15:00:00Z",
  "fields_verified": [
    "api_key",
    "organization_id"
  ],
  "credentials_masked": true,
  "ttl_seconds": 3600,
  "expiry_timestamp": "2026-04-24T16:00:00Z",
  "next_action": "proceed_to_execution_authorization"
}
```

### 3.2 Failure Response

```json
{
  "verification_type": "openai|telegram",
  "status": "fail",
  "timestamp": "2026-04-24T15:00:00Z",
  "failure_reason": "invalid_credentials|expired_credentials|revoked_credentials",
  "failed_fields": ["api_key"],
  "ttl_seconds": 0,
  "expiry_timestamp": null,
  "next_action": "retry_verification|notify_human"
}
```

### 3.3 Stale Response

```json
{
  "verification_type": "openai|telegram",
  "status": "stale",
  "timestamp": "2026-04-24T15:00:00Z",
  "failure_reason": "result_expired",
  "expiry_timestamp": "2026-04-24T14:00:00Z",
  "next_action": "re_verify_credentials"
}
```

---

## CHAPTER 4: Secret Masking Rules

### 4.1 DO NOT

- DO NOT log actual credentials
- DO NOT include credentials in RETURN_TO_CHATGPT
- DO NOT commit credentials to repository
- DO NOT store plaintext secrets

### 4.2 DO

- DO mask all credentials in logs
- DO use REDACTED placeholders
- DO verify format only
- DO record verification timestamp
- DO set TTL and expiry

---

## CHAPTER 5: Fixture Validation

### 5.1 Validation Script

This fixture can be validated using:

```bash
python scripts/validation/validate_evidence.py \
  --manifest manifests/phase2_api_automode_live_credential_verification_result.yaml \
  --repo-root .
```

### 5.2 Expected Results

- validate_evidence.py: PASS
- check_forbidden_changes.py: PASS
- check_required_evidence.py: PASS
- check_branch_workflow.py: PASS

---

*Live verification result fixture for Phase 2 API auto-mode.*
*Defines result format, states, and secret masking rules.*
*NO real credentials - all values are REDACTED.*