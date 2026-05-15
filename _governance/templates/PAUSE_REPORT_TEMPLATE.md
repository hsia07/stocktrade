# PAUSE Report Template (RETURN_TO_CHATGPT Formal Body)

round_id:
  <round_id>

task_type:
  pause_report

status:
  completed

formal_status_code:
  PAUSE_REPORT_GENERATED

pause_reason:
  manual_pause_requested / paused_after_failure / auto_paused_by_stall / auto_paused_by_no_new_commit_rtc / paused_by_usage

pause_sub_reason:
  insufficient_balance / api_quota_exhausted / model_unavailable / usage_source_unavailable / repeated_failure / silence_or_stall / NONE

last_known_head:
  <commit_hash>

run_state:
  paused / stopped

main_control_loop_running_true_or_false:
  FALSE

r030_dispatch_started_true_or_false:
  FALSE

trading_core_started_true_or_false:
  FALSE

broker_started_true_or_false:
  FALSE

execution_started_true_or_false:
  FALSE

live_mode_started_true_or_false:
  FALSE

order_execution_allowed_true_or_false:
  FALSE

pause_context:
  <brief description of what was happening when pause triggered>

checkpoint_saved_true_or_false:
  TRUE / FALSE

pause_flag_created_true_or_false:
  TRUE

telegram_notification_sent_true_or_false:
  TRUE / FALSE

usage_exhaustion_not_code_failure_true_or_false:
  TRUE / FALSE
  (note: pause by usage exhaustion is NOT a code failure; no retry, no model switch, no key rotation)

no_auto_retry_required_true_or_false:
  TRUE

manual_resume_required_true_or_false:
  TRUE

pre_resume_checks_required_before_resume_true_or_false:
  TRUE

recommended_next_action:
  WAIT_FOR_USER_MANUAL_START_OR_EXPLICIT_RESUME_AUTHORIZATION

final_recommendation:
  SYSTEM_PAUSED_AWAITING_USER_DECISION

prohibited_actions:
  - auto-retry: PROHIBITED
  - auto-model-switch: PROHIBITED
  - auto-key-rotation: PROHIBITED
  - auto-continue-after-recharge: PROHIBITED
  - auto-resume: PROHIBITED
  - main_control_loop restart: PROHIBITED
  - R030 dispatch: PROHIBITED
  - trading/broker/execution/live start: PROHIBITED
  - order_execution_allowed=TRUE: PROHIBITED
  - merge/push/promote: PROHIBITED
  - --no-verify: PROHIBITED
  - force push: PROHIBITED
