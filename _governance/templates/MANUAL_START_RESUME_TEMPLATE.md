# Manual /start Resume Authorization Template (RETURN_TO_CHATGPT Formal Body)

round_id:
  <round_id>

task_type:
  manual_start_resume_authorization

status:
  completed / blocked

formal_status_code:
  RESUME_AUTHORIZED_BY_USER / RESUME_NOT_AUTHORIZED

## User Authorization

user_authorization_source:
  telegram /start / panel_start / written_instruction / other

authorization_timestamp:
  <timestamp>

authorization_traceable_true_or_false:
  TRUE

resume_target:
  <specific round or operation to resume>

## Authorization Scope

resume_target_exact:
  <exact target>

allowed_commands:
  - resume specified target only
  - pre-resume checks execution
  - RETURN_TO_CHATGPT generation after resume attempt

prohibited_commands:
  - auto-advance to next round: PROHIBITED
  - dispatch R030 without separate authorization: PROHIBITED
  - merge: PROHIBITED (requires separate signoff)
  - push: PROHIBITED (requires separate signoff)
  - promote: PROHIBITED
  - PR creation: PROHIBITED
  - --no-verify: PROHIBITED
  - force push: PROHIBITED
  - trading/broker/execution/live start: PROHIBITED
  - order_execution_allowed=TRUE: PROHIBITED
  - main_control_loop start: PROHIBITED (requires separate authorization)

no_bundled_approval_true_or_false:
  TRUE
  (this authorization covers resume only. merge/push/promote each require separate user signoff.)

no_auto_continuation_true_or_false:
  TRUE
  (resume authorization does NOT imply continuation to subsequent rounds)

## Pre-Resume Check Requirement

pre_resume_checks_required_true_or_false:
  TRUE

pre_resume_checks_passed_true_or_false:
  <TRUE/FALSE after execution>

## Post-Resume Requirement

return_to_chatgpt_required_after_resume_attempt_true_or_false:
  TRUE

recommended_next_action:
  EXECUTE_PRE_RESUME_CHECKS_THEN_RESUME_IF_PASS

final_recommendation:
  RESUME_AUTHORIZED_AWAITING_PREFLIGHT_AND_EXECUTION
