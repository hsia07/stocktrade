# Phase 2 API Auto-Mode Credential Verification Fixture

## OpenAI API / Telegram Credential Verification Format

**Document Version:** 1.0
**Status:** CANDIDATE - fixture only, no real credentials
**Purpose:** Define credential verification format for API auto-mode

---

## IMPORTANT — NO REAL CREDENTIALS

This fixture defines the **format** for credential verification. It does NOT contain:
- Real OpenAI API keys
- Real Telegram bot tokens
- Real chat IDs or user IDs

All credential values in this document are **REDACTED** or **EXAMPLE FORMAT ONLY**.

---

## CHAPTER 1: OpenAI Credential Verification

### 1.1 Required Fields

| Field | Type | Format | Required | Example |
|-------|------|--------|----------|---------|
| api_key | string | sk-... | YES | sk-...REDACTED |
| organization_id | string | org-... | NO | org-...REDACTED |
| project_id | string | proj-... | NO | proj-...REDACTED |

### 1.2 Format Verification Rules

- api_key must start with "sk-" or "sk-proj-"
- organization_id must start with "org-"
- project_id must start with "proj-"

### 1.3 Redacted Example

```json
{
  "openai_credentials": {
    "api_key": "sk-...REDACTED",
    "organization_id": "org-...REDACTED",
    "project_id": "proj-...REDACTED"
  },
  "verification_status": "PASSED|FAILED",
  "verification_timestamp": "2026-04-24T14:00:00Z",
  "failure_reason": null
}
```

---

## CHAPTER 2: Telegram Credential Verification

### 2.1 Required Fields

| Field | Type | Format | Required | Example |
|-------|------|--------|----------|---------|
| bot_token | string | {digits}:{alphanumeric} | YES | 1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqr...REDACTED |
| chat_id | string | -{digits} or {digits} | NO | -0000000000:REDACTED |
| user_id | string | {digits} | NO | 0000000000:REDACTED |

### 2.2 Format Verification Rules

- bot_token must match pattern: \d+:[A-Za-z0-9_-]+
- chat_id must be numeric (optionally prefixed with -)
- user_id must be numeric

### 2.3 Redacted Example

```json
{
  "telegram_credentials": {
    "bot_token": "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqr...REDACTED",
    "chat_id": "-0000000000:REDACTED",
    "user_id": "0000000000:REDACTED"
  },
  "verification_status": "PASSED|FAILED",
  "verification_timestamp": "2026-04-24T14:00:00Z",
  "failure_reason": null
}
```

---

## CHAPTER 3: Verification Response Format

### 3.1 Success Response

```json
{
  "verification_type": "openai|telegram",
  "status": "passed",
  "timestamp": "2026-04-24T14:00:00Z",
  "fields_verified": [
    "api_key_format",
    "organization_id_format"
  ],
  "credentials_masked": true,
  "next_action": "proceed_to_execution_authorization"
}
```

### 3.2 Failure Response

```json
{
  "verification_type": "openai|telegram",
  "status": "failed",
  "timestamp": "2026-04-24T14:00:00Z",
  "failure_reason": "missing_required_field|invalid_format|credential_expired",
  "failed_fields": ["api_key"],
  "next_action": "retry_verification|notify_human"
}
```

---

## CHAPTER 4: Secret Masking Rules

### 4.1 DO NOT

- DO NOT log actual credentials
- DO NOT include credentials in RETURN_TO_CHATGPT
- DO NOT commit credentials to repository
- DO NOT validate credentials against live services

### 4.2 DO

- DO mask all credentials in logs
- DO use REDACTED placeholders
- DO verify format only
- DO record verification timestamp

---

## CHAPTER 5: Fixture Validation

### 5.1 Validation Script

This fixture can be validated using:

```bash
python scripts/validation/validate_evidence.py \
  --manifest manifests/phase2_api_automode_external_dependency_verification.yaml \
  --repo-root .
```

### 5.2 Expected Results

- validate_evidence.py: PASS
- check_forbidden_changes.py: PASS
- check_required_evidence.py: PASS
- check_branch_workflow.py: PASS

---

*Credential verification fixture for Phase 2 API auto-mode.*
*Defines credential format, verification response, and secret masking rules.*
*NO real credentials - all values are REDACTED.*