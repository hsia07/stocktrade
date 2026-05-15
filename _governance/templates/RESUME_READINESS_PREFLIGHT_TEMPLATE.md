# Resume Readiness Preflight Template (RETURN_TO_CHATGPT Formal Body)

round_id:
  <round_id>

task_type:
  resume_readiness_preflight

status:
  completed / blocked

formal_status_code:
  RESUME_READINESS_PREFLIGHT_PASS / RESUME_READINESS_PREFLIGHT_BLOCKED

## Preflight Checks

check_1_local_remote_head_match_true_or_false:
  TRUE / FALSE
  local: <local_hash>
  remote: <remote_hash>

check_2_git_status_clean_true_or_false:
  TRUE / FALSE
  status: <actual git status>

check_3_run_state_valid_true_or_false:
  TRUE / FALSE
  expected: stopped or paused
  actual: <run_state>

check_4_main_control_loop_not_running_true_or_false:
  TRUE / FALSE

check_5_no_dispatch_started_true_or_false:
  TRUE / FALSE
  r030_dispatch: <TRUE/FALSE>
  any_round_dispatch: <TRUE/FALSE>

check_6_trading_broker_execution_live_all_false_true_or_false:
  TRUE / FALSE
  trading: <status>
  broker: <status>
  execution: <status>
  live: <status>

check_7_order_execution_allowed_false_true_or_false:
  TRUE / FALSE

check_8_last_return_to_chatgpt_valid_true_or_false:
  TRUE / FALSE
  last_rtc: <path or reference>

check_9_pause_reason_resolved_true_or_false:
  TRUE / FALSE
  pause_reason: <reason>
  resolution_evidence: <evidence that resources are restored>

check_10_user_resume_authorized_true_or_false:
  TRUE / FALSE
  authorization_source: <telegram /start / panel / written>

## Result

can_resume_true_or_false:
  TRUE / FALSE

blocker_summary:
  NONE / <list of failed checks>

recommended_next_action:
  PROCEED_WITH_RESUME / STAY_PAUSED_REVIEW_BLOCKERS

final_recommendation:
  RESUME_READY_AWAITING_USER_CONFIRMATION / RESUME_BLOCKED_REQUIRES_RESOLUTION
