# UI_VISIBLE_ROUND_ACCEPTANCE_GATE Specification (P0)
# 使用者可見畫面接受閘門規格書

## Document ID: GOV-UI-VISIBLE-GATE-SPEC-001
## Version: 1.0
## Date: 2026-05-19
## Law Compliance: 04

============================================================================
SECTION 1: GATE OVERVIEW
============================================================================

Purpose:
  Establish mandatory acceptance gate for ANY round/task/candidate/merge/
  acceptance whose scope includes user-visible UI surfaces. This gate
  prevents UI rounds from being accepted based solely on test pass counts,
  artifact presence, or source file existence, without actual visible
  surface evidence.

Philosophy:
  "A UI is not done until a human (or equivalent mechanical scan) has
   confirmed what a user would actually see."

Scope:
  This gate applies to any round where the subject matter, task name,
  file paths, or acceptance criteria match the applicability triggers
  defined in Section 2.

============================================================================
SECTION 2: APPLICABILITY TRIGGERS
============================================================================

This gate MUST be applied to any round containing ANY of the following
trigger terms in its name, scope, description, files, or acceptance:

  UI                  user-facing         frontend
  index.html          dashboard           panel
  report              homepage            onboarding
  新手                教學                摘要
  手機                行動版              介面
  可視化              查詢                股票查詢
  模擬交易介面         緊急接管            六大 AI 會議可視化
  使用者可見畫面       肉眼驗證            DOM / screenshot / text evidence

If the round is contract-only (backend schema, test, artifact, read-only
state, non-visible foundation), the gate still applies but with the
contract-only disclosure in Section 7.

============================================================================
SECTION 3: VISIBLE SURFACE EVIDENCE REQUIREMENT
============================================================================

RATIONALE:
  UI rounds MUST NOT be accepted using only:
  - pytest pass counts
  - artifact file existence
  - source file existence
  - "all tests pass" as sole evidence

MANDATORY RETURN_TO_CHATGPT FIELDS:

  expected_visible_surface:
    <description of what the user should see>

  actual_visible_surface:
    <description of what was confirmed to exist>

  visible_surface_verified_true_or_false:
    TRUE / FALSE

  visible_surface_evidence_type:
    DOM / text scan / screenshot / manual preview / browser automation / other

  screenshot_or_dom_evidence_provided_true_or_false:
    TRUE / FALSE

FAIL CONDITION:
  If visible_surface_verified_true_or_false = FALSE for a UI round,
  the round SHALL be rejected as incomplete.

============================================================================
SECTION 4: PLACEHOLDER / MOJIBAKE SCAN REQUIREMENT
============================================================================

RATIONALE:
  Visible UI MUST NOT contain developer placeholders, untranslated
  English fragments, mojibake (encoding corruption), or filler labels
  that would confuse users.

SCANNED PATTERNS (non-exhaustive):
  - "SHORT Entry" / "SHORT SHORT"
  - "Entry?" / "EntryEntry" / "EntrySHORT"
  - "Lorem ipsum" / "filler" / "placeholder"
  - mojibake / 亂碼 / garbled text
  - untranslated developer placeholder strings
  - mixed English-Chinese placeholder fragments

EXCEPTIONS:
  - Logic-bound protocol keywords (e.g., "SHORT" in signal direction
    labels with clear semantic meaning) are EXEMPT.
  - All other matches MUST be documented.

MANDATORY RETURN_TO_CHATGPT FIELDS:

  placeholder_mojibake_scan_pass_true_or_false:
    TRUE / FALSE

  placeholder_mojibake_remaining:
    NONE / <list of remaining items with justification>

FAIL CONDITION:
  If placeholder_mojibake_scan_pass_true_or_false = FALSE and remaining
  items are NOT logic-bound protocol keywords, the round SHALL be rejected.

============================================================================
SECTION 5: FAKE FEATURE CLAIM PROHIBITION
============================================================================

RATIONALE:
  UI copy or structure MUST NOT falsely imply that unimplemented features
  are complete.

PROHIBITED EXAMPLES (non-exhaustive):
  - Market query UI exists but no backend → "全市場查詢已啟用" not allowed
  - Six-AI meeting cards with no data → "六大 AI 會議已完成" not allowed
  - Fubon API not connected → "富邦已連線" not allowed
  - Broker/execution/live not active → "實盤可用" not allowed
  - order_execution_allowed = FALSE → any "可下單" claim not allowed
  - Empty cards/pages claiming meeting/summary/query/simulation done

MANDATORY RETURN_TO_CHATGPT FIELDS:

  fake_feature_claim_detected_true_or_false:
    TRUE / FALSE

  fake_feature_claim_examples:
    NONE / <list of detected claims>

FAIL CONDITION:
  If fake_feature_claim_detected_true_or_false = TRUE, the round SHALL
  be rejected immediately.

============================================================================
SECTION 6: NO TRADING CONTROL POLLUTION
============================================================================

RATIONALE:
  UI rounds MUST NOT introduce unauthorized trading controls or bypass
  existing safety invariants.

MANDATORY CHECKS:
  - No buy/sell/approve/reject/order controls unless explicitly authorized
  - No broker/Fubon API/execution/live controls
  - No mode toggle that can switch to LIVE (unless live-readiness governance
    explicitly authorizes it)
  - No order_execution_allowed toggle
  - order_execution_allowed remains FALSE unless separate live-readiness
    approval exists

MANDATORY RETURN_TO_CHATGPT FIELDS:

  ui_trading_control_pollution_detected_true_or_false:
    FALSE

  buy_sell_approve_order_controls_added_true_or_false:
    FALSE

  broker_execution_live_controls_added_true_or_false:
    FALSE

  order_execution_allowed_true_or_false:
    FALSE

FAIL CONDITION:
  If any unauthorized trading control is detected, the round SHALL be
  rejected.

============================================================================
SECTION 7: CONTRACT-ONLY DISCLOSURE
============================================================================

RATIONALE:
  Rounds that only deliver contract, schema, test, artifact, backend module,
  or read-only state (no visible UI surface) MUST explicitly disclose this
  and MUST NOT claim UI completeness.

MANDATORY RETURN_TO_CHATGPT FIELDS:

  contract_only_not_ui_complete_true_or_false:
    TRUE / FALSE

  If TRUE, formal_status_code MUST be:
    CONTRACT_ONLY_NOT_UI_COMPLETE

  If FALSE, the round MUST satisfy all other sections of this gate.

============================================================================
SECTION 8: BACKEND / RUNTIME BOUNDARY
============================================================================

RATIONALE:
  UI rounds MUST NOT incidentally modify backend or runtime behavior
  unless explicitly authorized.

PROHIBITED CHANGES:
  - New API endpoint added
  - /api/state runtime behavior modified
  - Runtime state written
  - main_control_loop started
  - start_loop.ps1 executed
  - GOV-INT-005 started
  - Broker/execution/live integration
  - Fubon API integration

FAIL CONDITION:
  Any unauthorized backend/runtime change SHALL cause immediate rejection.

============================================================================
SECTION 9: MINIMUM TEST REQUIREMENTS
============================================================================

UI rounds MUST include automated tests covering at minimum:

  1. Visible element / DOM / text contract test
  2. Placeholder / mojibake negative test
  3. No fake feature claim test
  4. No trading controls test
  5. No secret rendering test
  6. No backend/runtime boundary pollution test
  7. Existing safety invariants preserved test

For Core-A4 or shadow snapshot related rounds, additionally:
  - core-a4-shadow-panel preserved
  - shadow-body preserved
  - renderCoreAShadow preserved
  - data.core_a_shadow_snapshot path preserved
  - order_execution_allowed display remains FALSE / read-only

============================================================================
SECTION 10: SECRET / CREDENTIAL SCAN
============================================================================

MANDATORY CHECK:
  Visible UI MUST NOT render:
  - API keys / apiKey / api_key
  - Secret tokens / secret_token
  - chat_id
  - Broker credentials
  - Fubon API credentials
  - Any credentials or secrets in plain text

MANDATORY RETURN_TO_CHATGPT FIELD:

  secret_values_rendered_in_ui_true_or_false:
    FALSE

FAIL CONDITION:
  If secret_values_rendered_in_ui_true_or_false = TRUE, the round SHALL
  be rejected.

============================================================================
SECTION 11: MOBILE / RESPONSIVE CHECK (RECOMMENDED)
============================================================================

For UI rounds targeting mobile or variable-width surfaces:

  mobile_or_responsive_check_done_true_or_false:
    TRUE / FALSE

  mobile_or_responsive_check_result:
    PASS / WARNING / NOT_APPLICABLE_WITH_REASON

============================================================================
SECTION 12: MANDATORY RETURN_TO_CHATGPT FIELDS (COMPLETE LIST)
============================================================================

Every UI-applicable round MUST include all of the following in
RETURN_TO_CHATGPT:

  ui_visible_round_gate_applied_true_or_false: TRUE / FALSE
  ui_visible_round_gate_applicability_reason: <reason>

  expected_visible_surface: <list>
  actual_visible_surface: <list>
  visible_surface_verified_true_or_false: TRUE / FALSE
  visible_surface_evidence_type: <type>
  screenshot_or_dom_evidence_provided_true_or_false: TRUE / FALSE

  placeholder_mojibake_scan_pass_true_or_false: TRUE / FALSE
  placeholder_mojibake_remaining: NONE / <list>

  fake_feature_claim_detected_true_or_false: TRUE / FALSE
  fake_feature_claim_examples: NONE / <list>

  contract_only_not_ui_complete_true_or_false: TRUE / FALSE

  ui_trading_control_pollution_detected_true_or_false: FALSE
  buy_sell_approve_order_controls_added_true_or_false: FALSE
  broker_execution_live_controls_added_true_or_false: FALSE
  order_execution_allowed_true_or_false: FALSE

  secret_values_rendered_in_ui_true_or_false: FALSE

  mobile_or_responsive_check_done_true_or_false: TRUE / FALSE
  mobile_or_responsive_check_result: <result>

============================================================================
SECTION 13: DIRECT FAIL CONDITIONS
============================================================================

ANY of the following SHALL cause DIRECT FAIL of the round:

  DF01: UI round does not reference UI_VISIBLE_ROUND_ACCEPTANCE_GATE
  DF02: No expected_visible_surface specified
  DF03: No actual_visible_surface specified
  DF04: No DOM/text/screenshot/manual preview evidence provided
  DF05: Tests only verify file existence, not visible UI content
  DF06: Visible UI contains SHORT/Entry/Entry?/EntryEntry/mojibake
        placeholders (excluding logic-bound protocol keywords)
  DF07: UI copy falsely implies unimplemented feature is complete
  DF08: Contract-only round claims UI complete without disclosure
  DF09: Unauthorized trading control added
  DF10: Unauthorized broker/execution/live control added
  DF11: Unauthorized LIVE mode toggle
  DF12: order_execution_allowed = TRUE without separate authorization
  DF13: Secret/token/chat_id/API key rendered in UI
  DF14: Unauthorized modification of server.py/server_v2.py/index.html/index_v2.html
  DF15: New API endpoint added without authorization
  DF16: Runtime/trading/broker/execution/live started without authorization
  DF17: R049 started without authorization
  DF18: Phase3 construction before UI_VISIBLE gate is governance-line active

============================================================================
SECTION 14: PHASE3 / R049 PRECONDITION
============================================================================

Before any R049 readiness or Phase3 construction can proceed, ALL of the
following MUST be confirmed:

  1. UI_VISIBLE_ROUND_ACCEPTANCE_GATE is formally incorporated into the
     governance line (this specification is part of that incorporation)

  2. Phase1+Phase2 full functional gap audit completed, OR user explicitly
     changes the ordering

  3. R022/R023/R024/R025/R026/R029/R040 visible UI gaps are NOT falsely
     marked as complete

============================================================================
SECTION 15: GATE COVERAGE MATRIX
============================================================================

  | Check | Layer | Mechanical | Enforced By | Status |
  |-------|-------|------------|-------------|--------|
  | Applicability triggers | Governance text | PARTIAL | Manual review | ACTIVE |
  | Visible surface evidence | Governance text | PARTIAL | Manual + RETURN_TO_CHATGPT | ACTIVE |
  | Placeholder/mojibake scan | Governance + test | PARTIAL | Automated test + scan | ACTIVE |
  | Fake feature claim | Governance + test | PARTIAL | Automated test + scan | ACTIVE |
  | Trading control pollution | Governance + test | PARTIAL | Automated test + scan | ACTIVE |
  | Backend/runtime boundary | Governance + test | PARTIAL | Automated test + scan | ACTIVE |
  | Contract-only disclosure | Governance text | PARTIAL | Manual review | ACTIVE |
  | Secret/credential scan | Governance + test | PARTIAL | Automated test + scan | ACTIVE |
  | Minimum test requirements | Governance text | PARTIAL | Manual review | ACTIVE |
  | Phase3/R049 precondition | Governance text | PARTIAL | Manual review | ACTIVE |

============================================================================
END OF UI_VISIBLE_ROUND_ACCEPTANCE_GATE SPECIFICATION
============================================================================
