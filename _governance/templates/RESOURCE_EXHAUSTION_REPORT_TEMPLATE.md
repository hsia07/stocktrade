# Resource Exhaustion Report Template (RETURN_TO_CHATGPT Formal Body)

round_id:
  <round_id>

task_type:
  resource_exhaustion_report

status:
  completed

formal_status_code:
  RESOURCE_EXHAUSTION_REPORT_GENERATED

exhaustion_category:
  insufficient_balance / api_quota_exhausted / model_unavailable / usage_source_unavailable

exhaustion_details:
  insufficient_balance:
    account: <account_id>
    required_balance: <amount>
    current_balance: <amount>
    currency: <currency>
  api_quota_exhausted:
    api_provider: <provider>
    quota_type: rate_limit / token_quota / daily_limit
    reset_time: <timestamp>
  model_unavailable:
    model_name: <model>
    error_type: 503 / overload / deprecation / other
    estimated_restore: <timestamp or unknown>
  usage_source_unavailable:
    source: OpenCode / Aider / other
    reason: <reason>

last_known_head:
  <commit_hash>

run_state:
  paused

usage_exhaustion_not_code_failure_true_or_false:
  TRUE
  (this is a resource exhaustion event, NOT a code failure)

no_auto_retry_required_true_or_false:
  TRUE
  (no auto-retry on resource exhaustion; retry would waste remaining quota or incur unexpected charges)

no_auto_model_switch_true_or_false:
  TRUE
  (no automatic model switch; model selection is user governance decision)

no_auto_key_switch_true_or_false:
  TRUE
  (no automatic API key rotation; key rotation requires explicit governance)

manual_resume_required_true_or_false:
  TRUE
  (only manual /start or explicit user authorization may resume)

pre_resume_checks_required_true_or_false:
  TRUE
  (pre-resume checks must pass before any resume attempt)

current_operation_completed_true_or_false:
  FALSE / TRUE
  (FALSE unless explicitly proven otherwise)

recommended_next_action:
  WAIT_FOR_RESOURCE_RESTORATION_THEN_USER_MANUAL_START

final_recommendation:
  RESOURCE_EXHAUSTION_PAUSED_AWAITING_USER_DECISION

prohibited_actions:
  - auto-retry on exhaustion: PROHIBITED
  - auto-model-switch: PROHIBITED
  - auto-key-rotation: PROHIBITED
  - auto-continue after recharge: PROHIBITED
  - auto-resume: PROHIBITED
