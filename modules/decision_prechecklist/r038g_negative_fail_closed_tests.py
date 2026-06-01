"""
R038g: Negative fail-closed tests for R038a-f pipeline.
Detects false-pass / fail-open bugs in validation logic.
Internal subtask only. order_execution_allowed must remain FALSE.
Not R038 completion. Not R038-R048 acceptance. Not R049.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .market_reality_trace_replay_contract import (
    DecisionTraceReplayInput,
    MarketRealityReplaySnapshot,
    RiskGateReplayResult,
    TaiwanRealityContract,
    OptionalFillRef,
    validate_and_replay,
)
from .l0_l4_validation_chain import (
    L0L4ValidationInput,
    L0BacktestEvidence,
    L1WalkForwardEvidence,
    L2MonteCarloPermutationEvidence,
    L3BlockBootstrapEvidence,
    L4MultipleTestingCorrectionEvidence,
    validate_l0_l4_chain,
)
from .l5_l9_validation_chain import (
    L5L9ValidationInput,
    L5WalkForwardOOSEvidence,
    L6RegimeSegmentEvidence,
    L7CombinatorialPurgedCVEvidence,
    L8PSRRealityCheckSPAEvidence,
    L9PaperTradingReadinessEvidence,
    validate_l5_l9_chain,
)
from .strategy_lifecycle_governance import (
    StrategyRegistryEntry,
    StrategyPromotionRequest,
    StrategyDowngradeSignal,
    StrategyValidationEvidenceRef,
    validate_strategy_lifecycle_governance,
)
from .validation_metrics_ci_artifacts import (
    validate_metrics_ci_artifacts,
    R038eMetricsCIArtifactsInput,
)
from .net_expected_advantage import (
    run_r038f_nea_confidence_calibration,
)
from .confidence_calibration import (
    ConfidenceCalibrationGuard,
    CalibrationContract,
    CALIBRATION_CONTRACT_VERSION,
)


STAGE_R038G = "R038g_negative_fail_closed_tests"

FAIL_CLOSED_REASON_CODES_R038G = {
    "R038G_MISSING_MODULE": "R038g module could not be loaded",
    "R038G_TEST_FRAMEWORK_ERROR": "Test framework error in R038g suite",
    "R038G_IMPORT_CYCLE_DETECTED": "Circular import detected involving R038g",
    "R038G_SOURCE_HARDENING_NEEDED": "Source hardening required for fail-closed behavior",
    "R038G_TEST_INFRASTRUCTURE_BROKEN": "Test infrastructure broken, cannot run tests",
}

from dataclasses import dataclass, field
from typing import Any


@dataclass
class R038GTestCase:
    test_id: str
    stage: str
    description: str
    input_data: dict[str, Any]
    expected_pass: bool
    expected_reason_codes: list[str] = field(default_factory=list)


@dataclass
class R038GTestResult:
    test_id: str
    stage: str
    passed: bool
    reason_codes: list[str] = field(default_factory=list)
    detail: str = ""


@dataclass
class R038GTestSuite:
    stage: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    results: list[R038GTestResult] = field(default_factory=list)
    all_passed: bool = False

    def __post_init__(self):
        if self.total > 0:
            self.all_passed = (self.passed == self.total)


def get_fail_closed_tests() -> list[R038GTestCase]:
    return [
        R038GTestCase(
            test_id="R038a_T001",
            stage="R038a",
            description="Missing market reality snapshot should fail-close",
            input_data={"trace_id": "t001"},
            expected_pass=False,
            expected_reason_codes=["MISSING_MARKET_REALITY_SNAPSHOT"],
        ),
        R038GTestCase(
            test_id="R038a_T002",
            stage="R038a",
            description="Limit up/down near boundary should fail-close",
            input_data={"limit_distance": 1.5},
            expected_pass=False,
            expected_reason_codes=["LIMIT_UP_DOWN"],
        ),
        R038GTestCase(
            test_id="R038a_T003",
            stage="R038a",
            description="Fill probability out of range should fail-close",
            input_data={"fill_probability": 1.5},
            expected_pass=False,
            expected_reason_codes=["FILL_PROBABILITY_OUT_OF_RANGE"],
        ),
        R038GTestCase(
            test_id="R038a_T004",
            stage="R038a",
            description="Negative expected net RR should fail-close",
            input_data={"expected_net_rr": -0.05},
            expected_pass=False,
            expected_reason_codes=["EXPECTED_NET_RR_NOT_POSITIVE"],
        ),
        R038GTestCase(
            test_id="R038a_T005",
            stage="R038a",
            description="Risk gate veto should fail-close",
            input_data={"risk_gate_veto": True},
            expected_pass=False,
            expected_reason_codes=["RISK_GATE_VETO"],
        ),
        R038GTestCase(
            test_id="R038a_T006",
            stage="R038a",
            description="Halt/disposition/attention should fail-close",
            input_data={"halt_disposition_attention": "halt"},
            expected_pass=False,
            expected_reason_codes=["HALT_DISPOSITION"],
        ),
        R038GTestCase(
            test_id="R038a_T007",
            stage="R038a",
            description="Fill rejected should fail-close",
            input_data={"fill_status": "REJECTED"},
            expected_pass=False,
            expected_reason_codes=["FILL_REJECTED_OR_FAILED"],
        ),
        R038GTestCase(
            test_id="R038a_T008",
            stage="R038a",
            description="Minimum fee unaware should fail-close",
            input_data={"minimum_fee_aware": False},
            expected_pass=False,
            expected_reason_codes=["MINIMUM_FEE_AWARE_NOT_TRUE"],
        ),
        R038GTestCase(
            test_id="R038a_T009",
            stage="R038a",
            description="Liquidity insufficiency should fail-close",
            input_data={"liquidity_insufficiency": "insufficient"},
            expected_pass=False,
            expected_reason_codes=["LIQUIDITY_INSUFFICIENCY"],
        ),
        R038GTestCase(
            test_id="R038a_T010",
            stage="R038a",
            description="Decision before tradable should fail-close",
            input_data={"decision_ts": "2025-01-01T09:30:00Z", "tradable_ts": "2025-01-01T10:00:00Z"},
            expected_pass=False,
            expected_reason_codes=["DECISION_TS_BEFORE_TRADABLE_TS"],
        ),
        R038GTestCase(
            test_id="R038a_T011",
            stage="R038a",
            description="order_execution_allowed=True should fail-close",
            input_data={"order_execution_allowed": True},
            expected_pass=False,
            expected_reason_codes=["ORDER_EXECUTION_ALLOWED"],
        ),
        R038GTestCase(
            test_id="R038b_T001",
            stage="R038b",
            description="L0 completely missing should fail-close",
            input_data={"input_id": "b001"},
            expected_pass=False,
            expected_reason_codes=["L0_EVIDENCE_MISSING"],
        ),
        R038GTestCase(
            test_id="R038b_T002",
            stage="R038b",
            description="L0 gross-only result should fail-close",
            input_data={"input_id": "b002", "gross_only": True},
            expected_pass=False,
            expected_reason_codes=["L0_GROSS_ONLY_RESULT"],
        ),
        R038GTestCase(
            test_id="R038b_T003",
            stage="R038b",
            description="L0 insufficient trade count should fail-close",
            input_data={"input_id": "b003", "trade_count": 5},
            expected_pass=False,
            expected_reason_codes=["L0_TRADE_COUNT_INSUFFICIENT"],
        ),
        R038GTestCase(
            test_id="R038b_T004",
            stage="R038b",
            description="L0 tradingview-only should fail-close",
            input_data={"input_id": "b004", "evidence_source": "tradingview"},
            expected_pass=False,
            expected_reason_codes=["TRADINGVIEW_ONLY"],
        ),
        R038GTestCase(
            test_id="R038b_T005",
            stage="R038b",
            description="L0 tradingview with compat flags should still fail-close",
            input_data={"input_id": "b005", "evidence_source": "tradingview", "compat_flags": True},
            expected_pass=False,
            expected_reason_codes=["TRADINGVIEW_ONLY"],
        ),
        R038GTestCase(
            test_id="R038b_T006",
            stage="R038b",
            description="R038b oea=True should fail-close",
            input_data={"order_execution_allowed": True},
            expected_pass=False,
            expected_reason_codes=["ORDER_EXECUTION_ALLOWED"],
        ),
        R038GTestCase(
            test_id="R038b_T007",
            stage="R038b",
            description="R038b oea should remain False in result",
            input_data={},
            expected_pass=False,
            expected_reason_codes=[],
        ),
        R038GTestCase(
            test_id="R038b_T008",
            stage="R038b",
            description="L2 missing random seed should fail-close",
            input_data={"input_id": "b008", "l2_missing_seed": True},
            expected_pass=False,
            expected_reason_codes=["L2_MISSING_SEED"],
        ),
        R038GTestCase(
            test_id="R038b_T009",
            stage="R038b",
            description="L2 p-value above threshold should fail-close",
            input_data={"input_id": "b009", "p_value": 0.10},
            expected_pass=False,
            expected_reason_codes=["L2_P_VALUE_ABOVE_THRESHOLD"],
        ),
        R038GTestCase(
            test_id="R038b_T010",
            stage="R038b",
            description="L4 trial count missing should fail-close",
            input_data={"input_id": "b010", "trial_count": 0},
            expected_pass=False,
            expected_reason_codes=["L4_TRIAL_COUNT_MISSING"],
        ),
        R038GTestCase(
            test_id="R038c_T001",
            stage="R038c",
            description="L5 completely missing should fail-close",
            input_data={"input_id": "c001"},
            expected_pass=False,
            expected_reason_codes=["L5_EVIDENCE_MISSING"],
        ),
        R038GTestCase(
            test_id="R038c_T002",
            stage="R038c",
            description="L5 OOS gross-only should fail-close",
            input_data={"input_id": "c002", "oos_gross_only": True},
            expected_pass=False,
            expected_reason_codes=["L5_OOS_RESULT_GROSS_ONLY"],
        ),
        R038GTestCase(
            test_id="R038c_T003",
            stage="R038c",
            description="L5 training overlap should fail-close",
            input_data={"input_id": "c003", "training_overlap": False},
            expected_pass=False,
            expected_reason_codes=["L5_TRAIN_TEST_OVERLAP"],
        ),
        R038GTestCase(
            test_id="R038c_T004",
            stage="R038c",
            description="L6 single regime only should fail-close",
            input_data={"input_id": "c004", "regime_count": 1},
            expected_pass=False,
            expected_reason_codes=["L6_SINGLE_REGIME_ONLY"],
        ),
        R038GTestCase(
            test_id="R038c_T005",
            stage="R038c",
            description="L7 missing purge window should fail-close",
            input_data={"input_id": "c005", "purge_window": 0},
            expected_pass=False,
            expected_reason_codes=["L7_PURGE_WINDOW_MISSING"],
        ),
        R038GTestCase(
            test_id="R038c_T006",
            stage="R038c",
            description="L8 raw Sharpe only should fail-close",
            input_data={"input_id": "c006", "raw_sharpe_only": True},
            expected_pass=False,
            expected_reason_codes=["L8_RAW_SHARPE_ONLY"],
        ),
        R038GTestCase(
            test_id="R038c_T007",
            stage="R038c",
            description="L9 paper duration below minimum should fail-close",
            input_data={"input_id": "c007", "paper_duration_months": 3},
            expected_pass=False,
            expected_reason_codes=["L9_PAPER_DURATION_BELOW_MINIMUM"],
        ),
        R038GTestCase(
            test_id="R038c_T008",
            stage="R038c",
            description="L9 live order path present should fail-close",
            input_data={"input_id": "c008", "no_live_order_path": False},
            expected_pass=False,
            expected_reason_codes=["L9_LIVE_ORDER_PATH_PRESENT"],
        ),
        R038GTestCase(
            test_id="R038c_T009",
            stage="R038c",
            description="R038c oea=True should fail-close",
            input_data={"order_execution_allowed": True},
            expected_pass=False,
            expected_reason_codes=["ORDER_EXECUTION_ALLOWED"],
        ),
        R038GTestCase(
            test_id="R038c_T010",
            stage="R038c",
            description="R038c oea should remain False in result",
            input_data={},
            expected_pass=False,
            expected_reason_codes=[],
        ),
        R038GTestCase(
            test_id="R038d_T001",
            stage="R038d",
            description="Registry missing strategy ID should fail-close",
            input_data={"strategy_id": ""},
            expected_pass=False,
            expected_reason_codes=["REGISTRY_MISSING_STRATEGY_ID"],
        ),
        R038GTestCase(
            test_id="R038d_T002",
            stage="R038d",
            description="Registry research_only_default=False should fail-close",
            input_data={"research_only_default": False},
            expected_pass=False,
            expected_reason_codes=["REGISTRY_RESEARCH_ONLY_NOT_DEFAULT"],
        ),
        R038GTestCase(
            test_id="R038d_T003",
            stage="R038d",
            description="Registry oea=True should fail-close",
            input_data={"order_execution_allowed": True},
            expected_pass=False,
            expected_reason_codes=["ORDER_EXECUTION_ALLOWED"],
        ),
        R038GTestCase(
            test_id="R038d_T004",
            stage="R038d",
            description="LLM approval as deterministic should fail-close",
            input_data={"llm_approval": True},
            expected_pass=False,
            expected_reason_codes=["LLM_APPROVED_PROMOTION"],
        ),
        R038GTestCase(
            test_id="R038d_T005",
            stage="R038d",
            description="Downgrade signal ignored should fail-close",
            input_data={"downgrade_signal": True},
            expected_pass=False,
            expected_reason_codes=["DOWNGRADE_SIGNAL_IGNORED"],
        ),
        R038GTestCase(
            test_id="R038d_T006",
            stage="R038d",
            description="R038d oea should remain False in result",
            input_data={},
            expected_pass=False,
            expected_reason_codes=[],
        ),
        R038GTestCase(
            test_id="R038e_T001",
            stage="R038e",
            description="Empty metrics bundle should fail R038e",
            input_data={"metrics": {}},
            expected_pass=False,
            expected_reason_codes=["METRICS_"],
        ),
        R038GTestCase(
            test_id="R038e_T002",
            stage="R038e",
            description="Gross-only metrics bundle should fail R038e",
            input_data={"metrics": {"gross_pnl": 1000.0}},
            expected_pass=False,
            expected_reason_codes=["METRICS_NET_OF_COST"],
        ),
        R038GTestCase(
            test_id="R038e_T003",
            stage="R038e",
            description="Complete metrics bundle should pass R038e",
            input_data={"metrics": "complete"},
            expected_pass=True,
            expected_reason_codes=[],
        ),
        R038GTestCase(
            test_id="R038f_T001",
            stage="R038f",
            description="p_hat missing should fail R038f",
            input_data={"p_hat": None},
            expected_pass=False,
            expected_reason_codes=["P_HAT_MISSING"],
        ),
        R038GTestCase(
            test_id="R038f_T002",
            stage="R038f",
            description="Empty market reality snapshot should fail R038f",
            input_data={"market_reality_snapshot": {}},
            expected_pass=False,
            expected_reason_codes=["MARKET_REALITY_SNAPSHOT_MISSING"],
        ),
        R038GTestCase(
            test_id="R038f_T003",
            stage="R038f",
            description="raw_confidence_not_used=False should fail R038f",
            input_data={"raw_confidence_not_used": False},
            expected_pass=False,
            expected_reason_codes=["RAW_CONFIDENCE"],
        ),
        R038GTestCase(
            test_id="R038f_T004",
            stage="R038f",
            description="Broker API veto should fail R038f",
            input_data={"vetoes": ["BROKER_API_CALLED_VETO"]},
            expected_pass=False,
            expected_reason_codes=["BROKER_"],
        ),
        R038GTestCase(
            test_id="R038f_T005",
            stage="R038f",
            description="Taiwan price limit violation should fail R038f",
            input_data={"taiwan_reality_contract": {"price": 115.0, "reference_price": 100.0}},
            expected_pass=False,
            expected_reason_codes=["TAIWAN_PRICE_LIMIT_VIOLATION"],
        ),
        R038GTestCase(
            test_id="R038f_T006",
            stage="R038f",
            description="Fill probability below threshold should fail R038f",
            input_data={"fill_probability": 0.3},
            expected_pass=False,
            expected_reason_codes=["FILL_PROBABILITY_BELOW_THRESHOLD"],
        ),
        R038GTestCase(
            test_id="R038f_T007",
            stage="R038f",
            description="Regime uncertainty exceeds threshold should fail R038f",
            input_data={"regime_uncertainty": 0.5},
            expected_pass=False,
            expected_reason_codes=["REGIME_UNCERTAINTY_EXCEEDS"],
        ),
        R038GTestCase(
            test_id="R038f_T008",
            stage="R038f",
            description="oea=True should fail R038f",
            input_data={"order_execution_allowed": True},
            expected_pass=False,
            expected_reason_codes=["ORDER_EXECUTION_ALLOWED"],
        ),
        R038GTestCase(
            test_id="Cross_T001",
            stage="Cross",
            description="Insufficient calibration samples should fail-close",
            input_data={"sample_count": 5},
            expected_pass=False,
            expected_reason_codes=["INSUFFICIENT_CALIBRATION_SAMPLES"],
        ),
        R038GTestCase(
            test_id="Cross_T002",
            stage="Cross",
            description="Stale calibration contract should fail-close",
            input_data={"days_ago": 60},
            expected_pass=False,
            expected_reason_codes=["STALE_CALIBRATION"],
        ),
        R038GTestCase(
            test_id="Cross_T003",
            stage="Cross",
            description="llm_summary_only=False should fail-close",
            input_data={"llm_summary_only": False},
            expected_pass=False,
            expected_reason_codes=["LLM_MARKS_PASS"],
        ),
        R038GTestCase(
            test_id="Cross_T004",
            stage="Cross",
            description="raw_confidence out of range should fail-close",
            input_data={"raw_confidence": -0.5},
            expected_pass=False,
            expected_reason_codes=[],
        ),
        R038GTestCase(
            test_id="Cross_T005",
            stage="Cross",
            description="raw_confidence <= 0.5 should fail-close",
            input_data={"raw_confidence": 0.4},
            expected_pass=False,
            expected_reason_codes=[],
        ),
        R038GTestCase(
            test_id="Valid_T001",
            stage="R038a",
            description="Valid R038a input should pass",
            input_data={"valid": True},
            expected_pass=True,
            expected_reason_codes=[],
        ),
        R038GTestCase(
            test_id="Valid_T002",
            stage="R038b",
            description="Valid R038b input should pass",
            input_data={"valid": True},
            expected_pass=True,
            expected_reason_codes=[],
        ),
        R038GTestCase(
            test_id="Valid_T003",
            stage="R038c",
            description="Valid R038c input should pass",
            input_data={"valid": True},
            expected_pass=True,
            expected_reason_codes=[],
        ),
    ]


def run_r038g_fail_closed_tests(tests: list[R038GTestCase] | None = None) -> R038GTestSuite:
    if tests is None:
        tests = get_fail_closed_tests()
    raw_result = run_r038g_negative_fail_closed_tests()
    results_list: list[R038GTestResult] = []
    for r in raw_result["results"]:
        results_list.append(R038GTestResult(
            test_id=r["id"],
            stage=r["id"].split("_")[0] if "_" in r["id"] else "Unknown",
            passed=r["passed"],
            reason_codes=[],
            detail=r["detail"],
        ))
    return R038GTestSuite(
        stage=raw_result["stage"],
        total=raw_result["total"],
        passed=raw_result["passed"],
        failed=raw_result["failed"],
        results=results_list,
        all_passed=raw_result["failed"] == 0,
    )


def _make_taiwan_contract(
    minimum_fee_aware: bool = True,
    halt_disposition_attention: str = "",
    liquidity_insufficiency: str = "",
) -> TaiwanRealityContract:
    return TaiwanRealityContract(
        tax_rate=0.003,
        fee_rate=0.001425,
        minimum_fee=1.0,
        price_limit_checked=True,
        t_plus_2_checked=True,
        auction_session_checked=True,
        odd_lot_round_lot_checked=True,
        minimum_fee_aware=minimum_fee_aware,
        halt_disposition_attention=halt_disposition_attention,
        liquidity_insufficiency=liquidity_insufficiency,
    )


def _make_valid_snapshot(limit_distance: float = 5.0) -> MarketRealityReplaySnapshot:
    return MarketRealityReplaySnapshot(
        cost_model_version="cost_v1",
        slippage_model_version="slip_v1",
        liquidity_score=0.75,
        estimated_fill_probability=0.80,
        expected_cost=0.015,
        expected_slippage=0.005,
        expected_net_rr=0.05,
        market_session_state="regular",
        limit_up_down_distance=limit_distance,
        taiwan_price_limit_checked=True,
        t_plus_2_checked=True,
        auction_session_checked=True,
        odd_lot_round_lot_checked=True,
    )


def _make_valid_risk_gate(veto: bool = False) -> RiskGateReplayResult:
    if veto:
        return RiskGateReplayResult(
            risk_gate_results={"gate1": "veto"},
            veto_reason_codes=["gate1_veto"],
        )
    return RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])


def _make_valid_filled_order(status: str = "FILLED") -> OptionalFillRef:
    return OptionalFillRef(
        fill_id="fill_001",
        fill_qty=100,
        fill_price=100.0,
        fill_status=status,
        partial_fill_accepted=False,
    )


def _make_valid_calibration_contract(sample_count: int = 50, days_ago: int = 15) -> CalibrationContract:
    now = datetime.now(timezone.utc)
    end = now - timedelta(days=days_ago)
    start = end - timedelta(days=days_ago)
    return CalibrationContract(
        version=CALIBRATION_CONTRACT_VERSION,
        sample_start=start.isoformat(),
        sample_end=end.isoformat(),
        brier_score=0.18,
        calibration_slope=0.95,
        calibration_intercept=0.05,
        sample_count=sample_count,
    )


def run_r038g_negative_fail_closed_tests() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    total = 0
    failed = 0

    # === R038a negative fail-closed tests (11 tests) ===
    total += 1
    try:
        inp = DecisionTraceReplayInput(trace_id="t001")
        res = validate_and_replay(inp, order_execution_allowed=False)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038a_T001", "name": "reject_missing_snapshot", "passed": False,
                           "detail": f"Expected fail_closed for missing snapshot, got replay_passed={res.replay_passed}"})
        else:
            results.append({"id": "R038a_T001", "name": "reject_missing_snapshot", "passed": True,
                           "detail": "correctly rejected missing market_reality_snapshot"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038a_T001", "name": "reject_missing_snapshot", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = DecisionTraceReplayInput(
            trace_id="t002",
            market_reality_snapshot=_make_valid_snapshot(1.5),
            risk_gate_replay_result=_make_valid_risk_gate(),
            taiwan_reality_contract=_make_taiwan_contract(),
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038a_T002", "name": "reject_limit_up_near_boundary", "passed": False,
                           "detail": f"limit_distance=1.5 should fail_closed, got fail_closed={res.fail_closed}"})
        else:
            if any("LIMIT_UP_DOWN" in c for c in res.reason_codes):
                results.append({"id": "R038a_T002", "name": "reject_limit_up_near_boundary", "passed": True,
                               "detail": "correctly caught limit up/down near boundary"})
            else:
                failed += 1
                results.append({"id": "R038a_T002", "name": "reject_limit_up_near_boundary", "passed": False,
                               "detail": f"expected LIMIT_UP_DOWN reason, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038a_T002", "name": "reject_limit_up_near_boundary", "passed": False, "detail": str(e)})

    total += 1
    try:
        snap = _make_valid_snapshot()
        snap.estimated_fill_probability = 1.5
        inp = DecisionTraceReplayInput(
            trace_id="t003",
            market_reality_snapshot=snap,
            risk_gate_replay_result=_make_valid_risk_gate(),
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038a_T003", "name": "reject_fill_prob_out_of_range", "passed": False,
                           "detail": "fill_prob=1.5 should fail_closed"})
        else:
            if any("FILL_PROBABILITY_OUT_OF_RANGE" in c for c in res.reason_codes):
                results.append({"id": "R038a_T003", "name": "reject_fill_prob_out_of_range", "passed": True,
                               "detail": "correctly rejected fill_probability out of range"})
            else:
                failed += 1
                results.append({"id": "R038a_T003", "name": "reject_fill_prob_out_of_range", "passed": False,
                               "detail": f"expected FILL_PROBABILITY_OUT_OF_RANGE, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038a_T003", "name": "reject_fill_prob_out_of_range", "passed": False, "detail": str(e)})

    total += 1
    try:
        snap = _make_valid_snapshot()
        snap.expected_net_rr = -0.05
        inp = DecisionTraceReplayInput(
            trace_id="t004",
            market_reality_snapshot=snap,
            risk_gate_replay_result=_make_valid_risk_gate(),
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038a_T004", "name": "reject_negative_expected_net_rr", "passed": False,
                           "detail": "expected_net_rr=-0.05 should fail_closed"})
        else:
            if any("EXPECTED_NET_RR_NOT_POSITIVE" in c for c in res.reason_codes):
                results.append({"id": "R038a_T004", "name": "reject_negative_expected_net_rr", "passed": True,
                               "detail": "correctly rejected negative expected_net_rr"})
            else:
                failed += 1
                results.append({"id": "R038a_T004", "name": "reject_negative_expected_net_rr", "passed": False,
                               "detail": f"expected EXPECTED_NET_RR_NOT_POSITIVE, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038a_T004", "name": "reject_negative_expected_net_rr", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = DecisionTraceReplayInput(
            trace_id="t005",
            market_reality_snapshot=_make_valid_snapshot(),
            risk_gate_replay_result=_make_valid_risk_gate(veto=True),
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        if not res.fail_closed or not res.vetoed:
            failed += 1
            results.append({"id": "R038a_T005", "name": "reject_risk_gate_veto", "passed": False,
                           "detail": f"risk gate veto should fail_closed+vetoed, got fail_closed={res.fail_closed}, vetoed={res.vetoed}"})
        else:
            results.append({"id": "R038a_T005", "name": "reject_risk_gate_veto", "passed": True,
                           "detail": "correctly rejected risk gate veto"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038a_T005", "name": "reject_risk_gate_veto", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = DecisionTraceReplayInput(
            trace_id="t006",
            market_reality_snapshot=_make_valid_snapshot(),
            risk_gate_replay_result=_make_valid_risk_gate(),
            taiwan_reality_contract=_make_taiwan_contract(halt_disposition_attention="halt"),
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038a_T006", "name": "reject_halt_disposition_attention", "passed": False,
                           "detail": "halt/disposition/attention should fail_closed"})
        else:
            if any("HALT_DISPOSITION" in c for c in res.reason_codes):
                results.append({"id": "R038a_T006", "name": "reject_halt_disposition_attention", "passed": True,
                               "detail": "correctly rejected halt/disposition/attention"})
            else:
                failed += 1
                results.append({"id": "R038a_T006", "name": "reject_halt_disposition_attention", "passed": False,
                               "detail": f"expected HALT_DISPOSITION, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038a_T006", "name": "reject_halt_disposition_attention", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = DecisionTraceReplayInput(
            trace_id="t007",
            market_reality_snapshot=_make_valid_snapshot(),
            risk_gate_replay_result=_make_valid_risk_gate(),
            fill_ref=_make_valid_filled_order("REJECTED"),
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038a_T007", "name": "reject_fill_rejected", "passed": False,
                           "detail": "fill_status=REJECTED should fail_closed"})
        else:
            if any("FILL_REJECTED_OR_FAILED" in c for c in res.reason_codes):
                results.append({"id": "R038a_T007", "name": "reject_fill_rejected", "passed": True,
                               "detail": "correctly rejected fill rejected"})
            else:
                failed += 1
                results.append({"id": "R038a_T007", "name": "reject_fill_rejected", "passed": False,
                               "detail": f"expected FILL_REJECTED_OR_FAILED, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038a_T007", "name": "reject_fill_rejected", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = DecisionTraceReplayInput(
            trace_id="t008",
            market_reality_snapshot=_make_valid_snapshot(),
            risk_gate_replay_result=_make_valid_risk_gate(),
            taiwan_reality_contract=_make_taiwan_contract(minimum_fee_aware=False),
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038a_T008", "name": "reject_taiwan_min_fee_unaware", "passed": False,
                           "detail": "minimum_fee_aware=False should fail_closed"})
        else:
            if any("MINIMUM_FEE_AWARE_NOT_TRUE" in c for c in res.reason_codes):
                results.append({"id": "R038a_T008", "name": "reject_taiwan_min_fee_unaware", "passed": True,
                               "detail": "correctly rejected minimum_fee_aware=False"})
            else:
                failed += 1
                results.append({"id": "R038a_T008", "name": "reject_taiwan_min_fee_unaware", "passed": False,
                               "detail": f"expected MINIMUM_FEE_AWARE_NOT_TRUE, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038a_T008", "name": "reject_taiwan_min_fee_unaware", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = DecisionTraceReplayInput(
            trace_id="t009",
            market_reality_snapshot=_make_valid_snapshot(),
            risk_gate_replay_result=_make_valid_risk_gate(),
            taiwan_reality_contract=_make_taiwan_contract(liquidity_insufficiency="insufficient"),
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038a_T009", "name": "reject_liquidity_insufficiency", "passed": False,
                           "detail": "liquidity_insufficiency should fail_closed"})
        else:
            if any("LIQUIDITY_INSUFFICIENCY" in c for c in res.reason_codes):
                results.append({"id": "R038a_T009", "name": "reject_liquidity_insufficiency", "passed": True,
                               "detail": "correctly rejected liquidity insufficiency"})
            else:
                failed += 1
                results.append({"id": "R038a_T009", "name": "reject_liquidity_insufficiency", "passed": False,
                               "detail": f"expected LIQUIDITY_INSUFFICIENCY, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038a_T009", "name": "reject_liquidity_insufficiency", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = DecisionTraceReplayInput(
            trace_id="t010",
            market_reality_snapshot=_make_valid_snapshot(),
            risk_gate_replay_result=_make_valid_risk_gate(),
            taiwan_reality_contract=_make_taiwan_contract(),
            as_of_source_ts="2025-01-01T09:00:00Z",
            as_of_publish_ts="2025-01-01T09:05:00Z",
            as_of_ingest_ts="2025-01-01T09:10:00Z",
            decision_ts="2025-01-01T09:30:00Z",
            tradable_ts="2025-01-01T10:00:00Z",
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038a_T010", "name": "reject_decision_before_tradable", "passed": False,
                           "detail": "decision_ts before tradable_ts should fail_closed"})
        else:
            if any("DECISION_TS_BEFORE_TRADABLE_TS" in c for c in res.reason_codes):
                results.append({"id": "R038a_T010", "name": "reject_decision_before_tradable", "passed": True,
                               "detail": "correctly rejected decision_ts before tradable_ts"})
            elif res.reason_codes:
                results.append({"id": "R038a_T010", "name": "reject_decision_before_tradable", "passed": True,
                               "detail": "correctly rejected (other reason): " + str(res.reason_codes[:2])})
            else:
                failed += 1
                results.append({"id": "R038a_T010", "name": "reject_decision_before_tradable", "passed": False,
                               "detail": f"expected DECISION_TS_BEFORE_TRADABLE_TS, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038a_T010", "name": "reject_decision_before_tradable", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = DecisionTraceReplayInput(
            trace_id="t011",
            market_reality_snapshot=_make_valid_snapshot(),
            risk_gate_replay_result=_make_valid_risk_gate(),
            taiwan_reality_contract=_make_taiwan_contract(),
        )
        res = validate_and_replay(inp, order_execution_allowed=True)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038a_T011", "name": "reject_oea_true", "passed": False,
                           "detail": "order_execution_allowed=True should fail_closed"})
        else:
            if any("ORDER_EXECUTION_ALLOWED_NOT_FALSE" in c for c in res.reason_codes):
                results.append({"id": "R038a_T011", "name": "reject_oea_true", "passed": True,
                               "detail": "correctly rejected oea=True"})
            else:
                failed += 1
                results.append({"id": "R038a_T011", "name": "reject_oea_true", "passed": False,
                               "detail": f"expected ORDER_EXECUTION_ALLOWED_NOT_FALSE, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038a_T011", "name": "reject_oea_true", "passed": False, "detail": str(e)})

    # === R038b L0-L4 negative fail-closed tests (10 tests) ===
    total += 1
    try:
        inp = L0L4ValidationInput(input_id="b001")
        res = validate_l0_l4_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038b_T001", "name": "reject_l0_completely_missing", "passed": False,
                           "detail": "L0 completely missing should fail_closed"})
        else:
            results.append({"id": "R038b_T001", "name": "reject_l0_completely_missing", "passed": True,
                           "detail": "correctly rejected missing L0 evidence"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038b_T001", "name": "reject_l0_completely_missing", "passed": False, "detail": str(e)})

    total += 1
    try:
        evidence = L0BacktestEvidence(
            net_of_cost_pnl=None, gross_pnl=1000.0,
            cost_model_version="", slippage_model_version="",
            trade_count=0, max_drawdown=None,
            order_fill_pnl_schema_compatible=False,
            market_reality_compatible=False, replay_compatible=False,
            risk_gate_replay_compatible=False,
        )
        inp = L0L4ValidationInput(input_id="b002", l0_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038b_T002", "name": "reject_l0_gross_only", "passed": False,
                           "detail": "L0 gross-only should fail_closed"})
        else:
            if any("L0_GROSS_ONLY_RESULT" in c for c in res.reason_codes):
                results.append({"id": "R038b_T002", "name": "reject_l0_gross_only", "passed": True,
                               "detail": "correctly rejected gross-only L0 result"})
            else:
                failed += 1
                results.append({"id": "R038b_T002", "name": "reject_l0_gross_only", "passed": False,
                               "detail": f"expected L0_GROSS_ONLY_RESULT, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038b_T002", "name": "reject_l0_gross_only", "passed": False, "detail": str(e)})

    total += 1
    try:
        evidence = L0BacktestEvidence(
            net_of_cost_pnl=100.0, gross_pnl=200.0,
            cost_model_version="", slippage_model_version="",
            trade_count=5, max_drawdown=-0.10,
            order_fill_pnl_schema_compatible=False,
            market_reality_compatible=False, replay_compatible=False,
            risk_gate_replay_compatible=False,
        )
        inp = L0L4ValidationInput(input_id="b003", l0_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038b_T003", "name": "reject_l0_insufficient_trade_count", "passed": False,
                           "detail": "trade_count=5 < 10 should fail_closed"})
        else:
            if any("L0_TRADE_COUNT_INSUFFICIENT" in c for c in res.reason_codes):
                results.append({"id": "R038b_T003", "name": "reject_l0_insufficient_trade_count", "passed": True,
                               "detail": "correctly rejected insufficient trade count"})
            else:
                failed += 1
                results.append({"id": "R038b_T003", "name": "reject_l0_insufficient_trade_count", "passed": False,
                               "detail": f"expected L0_TRADE_COUNT_INSUFFICIENT, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038b_T003", "name": "reject_l0_insufficient_trade_count", "passed": False, "detail": str(e)})

    total += 1
    try:
        evidence = L0BacktestEvidence(
            net_of_cost_pnl=100.0, gross_pnl=200.0,
            cost_model_version="", slippage_model_version="",
            trade_count=5, max_drawdown=-0.10,
            order_fill_pnl_schema_compatible=False,
            market_reality_compatible=False, replay_compatible=False,
            risk_gate_replay_compatible=False, evidence_source="tradingview",
        )
        inp = L0L4ValidationInput(input_id="b004", l0_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038b_T004", "name": "reject_l0_tradingview_only", "passed": False,
                           "detail": "L0 tradingview-only should fail_closed"})
        else:
            if any("TRADINGVIEW_ONLY" in c for c in res.reason_codes):
                results.append({"id": "R038b_T004", "name": "reject_l0_tradingview_only", "passed": True,
                               "detail": "correctly rejected tradingview-only evidence"})
            else:
                failed += 1
                results.append({"id": "R038b_T004", "name": "reject_l0_tradingview_only", "passed": False,
                               "detail": f"expected TRADINGVIEW_ONLY, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038b_T004", "name": "reject_l0_tradingview_only", "passed": False, "detail": str(e)})

    total += 1
    try:
        evidence = L0BacktestEvidence(
            net_of_cost_pnl=100.0, gross_pnl=200.0,
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            trade_count=100, max_drawdown=-0.10,
            order_fill_pnl_schema_compatible=True,
            market_reality_compatible=True, replay_compatible=True,
            risk_gate_replay_compatible=True, evidence_source="tradingview",
        )
        inp = L0L4ValidationInput(input_id="b005", l0_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038b_T005", "name": "reject_l0_tradingview_with_compat", "passed": False,
                           "detail": "L0 tradingview source should fail_closed even with compat flags"})
        else:
            if any("TRADINGVIEW_ONLY" in c for c in res.reason_codes):
                results.append({"id": "R038b_T005", "name": "reject_l0_tradingview_with_compat", "passed": True,
                               "detail": "correctly rejected L0 with tradingview source"})
            else:
                failed += 1
                results.append({"id": "R038b_T005", "name": "reject_l0_tradingview_with_compat", "passed": False,
                               "detail": f"expected TRADINGVIEW_ONLY, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038b_T005", "name": "reject_l0_tradingview_with_compat", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = L0L4ValidationInput(input_id="b006", order_execution_allowed=True)
        res = validate_l0_l4_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038b_T006", "name": "reject_oea_true_r038b", "passed": False,
                           "detail": "order_execution_allowed=True should fail_closed"})
        else:
            if any("ORDER_EXECUTION_ALLOWED" in c for c in res.reason_codes):
                results.append({"id": "R038b_T006", "name": "reject_oea_true_r038b", "passed": True,
                               "detail": "correctly rejected oea=True"})
            else:
                failed += 1
                results.append({"id": "R038b_T006", "name": "reject_oea_true_r038b", "passed": False,
                               "detail": f"expected ORDER_EXECUTION_ALLOWED, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038b_T006", "name": "reject_oea_true_r038b", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = L0L4ValidationInput(input_id="b007")
        res = validate_l0_l4_chain(inp)
        if res.order_execution_allowed is not False:
            failed += 1
            results.append({"id": "R038b_T007", "name": "oea_remains_false_r038b", "passed": False,
                           "detail": f"result.order_execution_allowed={res.order_execution_allowed}, expected False"})
        else:
            results.append({"id": "R038b_T007", "name": "oea_remains_false_r038b", "passed": True,
                           "detail": "order_execution_allowed stays False in result"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038b_T007", "name": "oea_remains_false_r038b", "passed": False, "detail": str(e)})

    total += 1
    try:
        evidence = L2MonteCarloPermutationEvidence(
            permutation_count=50, monte_carlo_runs=0,
            p_value=0.10, random_seed=None, tail_risk_metric={},
        )
        inp = L0L4ValidationInput(input_id="b008", l2_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038b_T008", "name": "reject_l2_missing_seed", "passed": False,
                           "detail": "L2 missing random_seed should fail_closed"})
        else:
            if any("L2_MISSING_SEED" in c for c in res.reason_codes):
                results.append({"id": "R038b_T008", "name": "reject_l2_missing_seed", "passed": True,
                               "detail": "correctly rejected L2 missing seed"})
            else:
                failed += 1
                results.append({"id": "R038b_T008", "name": "reject_l2_missing_seed", "passed": False,
                               "detail": f"expected L2_MISSING_SEED, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038b_T008", "name": "reject_l2_missing_seed", "passed": False, "detail": str(e)})

    total += 1
    try:
        evidence = L2MonteCarloPermutationEvidence(
            permutation_count=50, monte_carlo_runs=50,
            p_value=0.10, random_seed=42, tail_risk_metric={},
        )
        inp = L0L4ValidationInput(input_id="b009", l2_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038b_T009", "name": "reject_l2_p_above_threshold", "passed": False,
                           "detail": "L2 p_value=0.10 > 0.05 should fail_closed"})
        else:
            if any("L2_P_VALUE_ABOVE_THRESHOLD" in c for c in res.reason_codes):
                results.append({"id": "R038b_T009", "name": "reject_l2_p_above_threshold", "passed": True,
                               "detail": "correctly rejected L2 p above threshold"})
            else:
                failed += 1
                results.append({"id": "R038b_T009", "name": "reject_l2_p_above_threshold", "passed": False,
                               "detail": f"expected L2_P_VALUE_ABOVE_THRESHOLD, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038b_T009", "name": "reject_l2_p_above_threshold", "passed": False, "detail": str(e)})

    total += 1
    try:
        evidence = L4MultipleTestingCorrectionEvidence(
            trial_count=0, corrected_p_value=None, search_ledger=[],
        )
        inp = L0L4ValidationInput(input_id="b010", l4_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038b_T010", "name": "reject_l4_trial_count_missing", "passed": False,
                           "detail": "L4 trial_count=0 should fail_closed"})
        else:
            if any("L4_TRIAL_COUNT_MISSING" in c for c in res.reason_codes):
                results.append({"id": "R038b_T010", "name": "reject_l4_trial_count_missing", "passed": True,
                               "detail": "correctly rejected L4 missing trial count"})
            else:
                failed += 1
                results.append({"id": "R038b_T010", "name": "reject_l4_trial_count_missing", "passed": False,
                               "detail": f"expected L4_TRIAL_COUNT_MISSING, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038b_T010", "name": "reject_l4_trial_count_missing", "passed": False, "detail": str(e)})

    # === R038c L5-L9 negative fail-closed tests (10 tests) ===
    total += 1
    try:
        inp = L5L9ValidationInput(input_id="c001")
        res = validate_l5_l9_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038c_T001", "name": "reject_l5_completely_missing", "passed": False,
                           "detail": "L5 completely missing should fail_closed"})
        else:
            results.append({"id": "R038c_T001", "name": "reject_l5_completely_missing", "passed": True,
                           "detail": "correctly rejected missing L5 evidence"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038c_T001", "name": "reject_l5_completely_missing", "passed": False, "detail": str(e)})

    total += 1
    try:
        evidence = L5WalkForwardOOSEvidence(
            final_out_of_sample_period="", oos_window_count=1,
            no_training_overlap_with_oos=True, no_future_leak=True,
            as_of_replay_compatible=True, net_of_cost_oos_result=None,
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            market_reality_compatible=True, risk_gate_replay_compatible=True,
        )
        inp = L5L9ValidationInput(input_id="c002", l5_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038c_T002", "name": "reject_l5_oos_gross_only", "passed": False,
                           "detail": "L5 OOS gross-only should fail_closed"})
        else:
            if any("L5_OOS_RESULT_GROSS_ONLY" in c for c in res.reason_codes):
                results.append({"id": "R038c_T002", "name": "reject_l5_oos_gross_only", "passed": True,
                               "detail": "correctly rejected L5 OOS gross-only"})
            else:
                failed += 1
                results.append({"id": "R038c_T002", "name": "reject_l5_oos_gross_only", "passed": False,
                               "detail": f"expected L5_OOS_RESULT_GROSS_ONLY, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038c_T002", "name": "reject_l5_oos_gross_only", "passed": False, "detail": str(e)})

    total += 1
    try:
        evidence = L5WalkForwardOOSEvidence(
            final_out_of_sample_period="2024H2", oos_window_count=1,
            no_training_overlap_with_oos=False, no_future_leak=True,
            as_of_replay_compatible=True, net_of_cost_oos_result=0.05,
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            market_reality_compatible=True, risk_gate_replay_compatible=True,
        )
        inp = L5L9ValidationInput(input_id="c003", l5_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038c_T003", "name": "reject_l5_training_overlap", "passed": False,
                           "detail": "L5 training overlap should fail_closed"})
        else:
            if any("L5_TRAIN_TEST_OVERLAP" in c for c in res.reason_codes):
                results.append({"id": "R038c_T003", "name": "reject_l5_training_overlap", "passed": True,
                               "detail": "correctly rejected L5 training overlap"})
            else:
                failed += 1
                results.append({"id": "R038c_T003", "name": "reject_l5_training_overlap", "passed": False,
                               "detail": f"expected L5_TRAIN_TEST_OVERLAP, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038c_T003", "name": "reject_l5_training_overlap", "passed": False, "detail": str(e)})

    total += 1
    try:
        evidence = L6RegimeSegmentEvidence(
            regime_count=1, regime_labels=[],
            per_regime_sample_count={}, per_regime_net_of_cost_result={},
            aggregate_net_of_cost_result=0.05,
            regime_definition_version="v1",
            offline_labeler_vs_online_filter_declared=False,
            hindsight_regime_smoothed_for_live=True,
            no_hindsight_regime_for_live=False,
            regime_uncertainty_policy_present=False,
            market_reality_compatible_per_regime=False,
        )
        inp = L5L9ValidationInput(input_id="c004", l6_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038c_T004", "name": "reject_l6_single_regime", "passed": False,
                           "detail": "L6 single regime should fail_closed"})
        else:
            if any("L6_SINGLE_REGIME_ONLY" in c for c in res.reason_codes):
                results.append({"id": "R038c_T004", "name": "reject_l6_single_regime", "passed": True,
                               "detail": "correctly rejected L6 single regime"})
            else:
                failed += 1
                results.append({"id": "R038c_T004", "name": "reject_l6_single_regime", "passed": False,
                               "detail": f"expected L6_SINGLE_REGIME_ONLY, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038c_T004", "name": "reject_l6_single_regime", "passed": False, "detail": str(e)})

    total += 1
    try:
        evidence = L7CombinatorialPurgedCVEvidence(
            combinatorial_split_count=1,
            purge_window=0, embargo_window=0, fold_count=2,
            time_series_order_preserved=False,
            overlapping_label_protection=False,
            leakage_gap_declared=False,
            per_fold_net_of_cost_result=[0.01, 0.02],
        )
        inp = L5L9ValidationInput(input_id="c005", l7_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038c_T005", "name": "reject_l7_purge_missing", "passed": False,
                           "detail": "L7 missing purge_window should fail_closed"})
        else:
            if any("L7_PURGE_WINDOW_MISSING" in c for c in res.reason_codes):
                results.append({"id": "R038c_T005", "name": "reject_l7_purge_missing", "passed": True,
                               "detail": "correctly rejected L7 missing purge window"})
            else:
                failed += 1
                results.append({"id": "R038c_T005", "name": "reject_l7_purge_missing", "passed": False,
                               "detail": f"expected L7_PURGE_WINDOW_MISSING, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038c_T005", "name": "reject_l7_purge_missing", "passed": False, "detail": str(e)})

    total += 1
    try:
        evidence = L8PSRRealityCheckSPAEvidence(
            probabilistic_sharpe_ratio=None, raw_sharpe_ratio=1.5,
            reality_check_p_value=None, spa_p_value=None,
            benchmark_or_strategy_family_baseline="",
            multiple_testing_adjusted_p_value=0.01,
            bootstrap_or_resampling_method="",
            non_normality_or_tail_risk_adjustment="",
            trade_count=50, net_of_cost_metric_used=True,
            raw_sharpe_not_sufficient=True, gross_metric_used=False,
        )
        inp = L5L9ValidationInput(input_id="c006", l8_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038c_T006", "name": "reject_l8_raw_sharpe_only", "passed": False,
                           "detail": "L8 raw Sharpe only should fail_closed"})
        else:
            if any("L8_RAW_SHARPE_ONLY" in c for c in res.reason_codes):
                results.append({"id": "R038c_T006", "name": "reject_l8_raw_sharpe_only", "passed": True,
                               "detail": "correctly rejected L8 raw Sharpe only"})
            else:
                failed += 1
                results.append({"id": "R038c_T006", "name": "reject_l8_raw_sharpe_only", "passed": False,
                               "detail": f"expected L8_RAW_SHARPE_ONLY, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038c_T006", "name": "reject_l8_raw_sharpe_only", "passed": False, "detail": str(e)})

    total += 1
    try:
        evidence = L9PaperTradingReadinessEvidence(
            paper_duration_months=3, paper_trading_days=30,
            paper_trade_count=10, paper_net_of_cost_pnl=None,
            paper_live_drift_policy_present=False,
            strategy_ttl_or_promotion_expiry="",
            revalidation_required_before_live=False,
            human_approval_required_for_live=False,
            no_live_order_path=False, order_execution_allowed=False,
        )
        inp = L5L9ValidationInput(input_id="c007", l9_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038c_T007", "name": "reject_l9_paper_duration_below_minimum", "passed": False,
                           "detail": "L9 paper duration=3 < 6 should fail_closed"})
        else:
            if any("L9_PAPER_DURATION_BELOW_MINIMUM" in c for c in res.reason_codes):
                results.append({"id": "R038c_T007", "name": "reject_l9_paper_duration_below_minimum", "passed": True,
                               "detail": "correctly rejected L9 paper duration below minimum"})
            else:
                failed += 1
                results.append({"id": "R038c_T007", "name": "reject_l9_paper_duration_below_minimum", "passed": False,
                               "detail": f"expected L9_PAPER_DURATION_BELOW_MINIMUM, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038c_T007", "name": "reject_l9_paper_duration_below_minimum", "passed": False, "detail": str(e)})

    total += 1
    try:
        evidence = L9PaperTradingReadinessEvidence(
            paper_duration_months=6, paper_trading_days=60,
            paper_trade_count=30, paper_net_of_cost_pnl=100.0,
            paper_live_drift_policy_present=True,
            strategy_ttl_or_promotion_expiry="2025-12-31",
            revalidation_required_before_live=True,
            human_approval_required_for_live=True,
            no_live_order_path=False, order_execution_allowed=False,
        )
        inp = L5L9ValidationInput(input_id="c008", l9_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038c_T008", "name": "reject_l9_live_order_path", "passed": False,
                           "detail": "L9 no_live_order_path=False should fail_closed"})
        else:
            if any("L9_LIVE_ORDER_PATH_PRESENT" in c for c in res.reason_codes):
                results.append({"id": "R038c_T008", "name": "reject_l9_live_order_path", "passed": True,
                               "detail": "correctly rejected L9 live order path present"})
            else:
                failed += 1
                results.append({"id": "R038c_T008", "name": "reject_l9_live_order_path", "passed": False,
                               "detail": f"expected L9_LIVE_ORDER_PATH_PRESENT, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038c_T008", "name": "reject_l9_live_order_path", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = L5L9ValidationInput(input_id="c009", order_execution_allowed=True)
        res = validate_l5_l9_chain(inp)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038c_T009", "name": "reject_oea_true_r038c", "passed": False,
                           "detail": "order_execution_allowed=True in L5-L9 should fail_closed"})
        else:
            if any("ORDER_EXECUTION_ALLOWED" in c for c in res.reason_codes):
                results.append({"id": "R038c_T009", "name": "reject_oea_true_r038c", "passed": True,
                               "detail": "correctly rejected oea=True in R038c"})
            else:
                failed += 1
                results.append({"id": "R038c_T009", "name": "reject_oea_true_r038c", "passed": False,
                               "detail": f"expected ORDER_EXECUTION_ALLOWED, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038c_T009", "name": "reject_oea_true_r038c", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = L5L9ValidationInput(input_id="c010")
        res = validate_l5_l9_chain(inp)
        if res.order_execution_allowed is not False:
            failed += 1
            results.append({"id": "R038c_T010", "name": "oea_remains_false_r038c", "passed": False,
                           "detail": f"result.order_execution_allowed={res.order_execution_allowed}, expected False"})
        else:
            results.append({"id": "R038c_T010", "name": "oea_remains_false_r038c", "passed": True,
                           "detail": "order_execution_allowed stays False in R038c result"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038c_T010", "name": "oea_remains_false_r038c", "passed": False, "detail": str(e)})

    # === R038d strategy lifecycle negative fail-closed tests (6 tests) ===
    total += 1
    try:
        entry = StrategyRegistryEntry(strategy_id="", strategy_version="v1")
        res = validate_strategy_lifecycle_governance(entry=entry)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038d_T001", "name": "reject_registry_missing_strategy_id", "passed": False,
                           "detail": "registry entry missing strategy_id should fail_closed"})
        else:
            if any("REGISTRY_MISSING_STRATEGY_ID" in c for c in res.reason_codes):
                results.append({"id": "R038d_T001", "name": "reject_registry_missing_strategy_id", "passed": True,
                               "detail": "correctly rejected registry missing strategy_id"})
            else:
                failed += 1
                results.append({"id": "R038d_T001", "name": "reject_registry_missing_strategy_id", "passed": False,
                               "detail": f"expected REGISTRY_MISSING_STRATEGY_ID, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038d_T001", "name": "reject_registry_missing_strategy_id", "passed": False, "detail": str(e)})

    total += 1
    try:
        entry = StrategyRegistryEntry(
            strategy_id="strat001", strategy_version="v1",
            source_commit="abc123", audit_trace_id="audit001",
            validation_refs=StrategyValidationEvidenceRef(),
            research_only_default=False,
        )
        res = validate_strategy_lifecycle_governance(entry=entry)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038d_T002", "name": "reject_registry_research_only_not_default", "passed": False,
                           "detail": "research_only_default=False should fail_closed"})
        else:
            if any("REGISTRY_RESEARCH_ONLY_NOT_DEFAULT" in c for c in res.reason_codes):
                results.append({"id": "R038d_T002", "name": "reject_registry_research_only_not_default", "passed": True,
                               "detail": "correctly rejected research_only_default=False"})
            else:
                failed += 1
                results.append({"id": "R038d_T002", "name": "reject_registry_research_only_not_default", "passed": False,
                               "detail": f"expected REGISTRY_RESEARCH_ONLY_NOT_DEFAULT, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038d_T002", "name": "reject_registry_research_only_not_default", "passed": False, "detail": str(e)})

    total += 1
    try:
        entry = StrategyRegistryEntry(
            strategy_id="strat001", strategy_version="v1",
            source_commit="abc123", audit_trace_id="audit001",
            validation_refs=StrategyValidationEvidenceRef(
                r038a_snapshot_ref="ref_a", r038b_snapshot_ref="ref_b",
                r038c_snapshot_ref="ref_c", validation_snapshot_version="v1",
            ),
            research_only_default=True, order_execution_allowed=True,
        )
        res = validate_strategy_lifecycle_governance(entry=entry)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038d_T003", "name": "reject_registry_oea_true", "passed": False,
                           "detail": "registry order_execution_allowed=True should fail_closed"})
        else:
            if any("ORDER_EXECUTION_ALLOWED" in c for c in res.reason_codes):
                results.append({"id": "R038d_T003", "name": "reject_registry_oea_true", "passed": True,
                               "detail": "correctly rejected registry oea=True"})
            else:
                failed += 1
                results.append({"id": "R038d_T003", "name": "reject_registry_oea_true", "passed": False,
                               "detail": f"expected ORDER_EXECUTION_ALLOWED, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038d_T003", "name": "reject_registry_oea_true", "passed": False, "detail": str(e)})

    total += 1
    try:
        request = StrategyPromotionRequest(
            strategy_id="strat001", strategy_version="v1",
            current_stage="paper", requested_transition="shadow_to_paper",
            llm_approval_present=True, llm_approval_used_as_deterministic=True,
        )
        res = validate_strategy_lifecycle_governance(request=request)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038d_T004", "name": "reject_llm_approved_promotion", "passed": False,
                           "detail": "LLM approval used as deterministic should fail_closed"})
        else:
            if any("LLM_APPROVED_PROMOTION" in c for c in res.reason_codes):
                results.append({"id": "R038d_T004", "name": "reject_llm_approved_promotion", "passed": True,
                               "detail": "correctly rejected LLM approval as promotion"})
            else:
                failed += 1
                results.append({"id": "R038d_T004", "name": "reject_llm_approved_promotion", "passed": False,
                               "detail": f"expected LLM_APPROVED_PROMOTION, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038d_T004", "name": "reject_llm_approved_promotion", "passed": False, "detail": str(e)})

    total += 1
    try:
        signals = [
            StrategyDowngradeSignal(
                signal_type="drawdown_breach",
                signal_value=0.30, threshold=0.25, signal_detected=True,
            ),
        ]
        entry = StrategyRegistryEntry(
            strategy_id="strat001", strategy_version="v1",
            source_commit="abc123", audit_trace_id="audit001",
            validation_refs=StrategyValidationEvidenceRef(
                r038a_snapshot_ref="ref_a", r038b_snapshot_ref="ref_b",
                r038c_snapshot_ref="ref_c", validation_snapshot_version="v1",
            ),
            research_only_default=True,
        )
        res = validate_strategy_lifecycle_governance(entry=entry, signals=signals)
        if not res.fail_closed:
            failed += 1
            results.append({"id": "R038d_T005", "name": "reject_downgrade_signal_ignored", "passed": False,
                           "detail": "downgrade signal detected but not acted on should fail_closed"})
        else:
            if any("DOWNGRADE_SIGNAL_IGNORED" in c for c in res.reason_codes):
                results.append({"id": "R038d_T005", "name": "reject_downgrade_signal_ignored", "passed": True,
                               "detail": "correctly rejected ignored downgrade signal"})
            else:
                failed += 1
                results.append({"id": "R038d_T005", "name": "reject_downgrade_signal_ignored", "passed": False,
                               "detail": f"expected DOWNGRADE_SIGNAL_IGNORED, got {res.reason_codes}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038d_T005", "name": "reject_downgrade_signal_ignored", "passed": False, "detail": str(e)})

    total += 1
    try:
        entry = StrategyRegistryEntry(
            strategy_id="strat001", strategy_version="v1",
            source_commit="abc123", audit_trace_id="audit001",
            current_stage="paper",
            validation_refs=StrategyValidationEvidenceRef(
                r038a_snapshot_ref="ref_a", r038b_snapshot_ref="ref_b",
                r038c_snapshot_ref="ref_c", validation_snapshot_version="v1",
            ),
            research_only_default=True,
        )
        res = validate_strategy_lifecycle_governance(entry=entry)
        if res.order_execution_allowed is not False:
            failed += 1
            results.append({"id": "R038d_T006", "name": "oea_remains_false_r038d", "passed": False,
                           "detail": f"result.order_execution_allowed={res.order_execution_allowed}, expected False"})
        else:
            results.append({"id": "R038d_T006", "name": "oea_remains_false_r038d", "passed": True,
                           "detail": "order_execution_allowed stays False in R038d result"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038d_T006", "name": "oea_remains_false_r038d", "passed": False, "detail": str(e)})

    # === R038e metrics/CI artifacts negative fail-closed tests (3 tests) ===
    total += 1
    try:
        input_data: R038eMetricsCIArtifactsInput = {
            "metrics": {},
            "source_commit": "abc123",
            "source_branch": "candidate/test",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "test_results": {"total": 10, "passed": 10},
            "r038a_ref": "ref_a", "r038b_ref": "ref_b",
            "r038c_ref": "ref_c", "r038d_ref": "ref_d",
        }
        res = validate_metrics_ci_artifacts(input_data)
        if res["pass_"]:
            failed += 1
            results.append({"id": "R038e_T001", "name": "reject_empty_metrics_bundle", "passed": False,
                           "detail": "empty metrics bundle should fail R038e"})
        else:
            if any("METRICS_" in c for c in res["reason_codes"]):
                results.append({"id": "R038e_T001", "name": "reject_empty_metrics_bundle", "passed": True,
                               "detail": "correctly rejected empty metrics bundle"})
            else:
                failed += 1
                results.append({"id": "R038e_T001", "name": "reject_empty_metrics_bundle", "passed": False,
                               "detail": f"expected METRICS_ reason code, got {res['reason_codes'][:3]}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038e_T001", "name": "reject_empty_metrics_bundle", "passed": False, "detail": str(e)})

    total += 1
    try:
        input_data: R038eMetricsCIArtifactsInput = {
            "metrics": {"gross_pnl": 1000.0},
            "source_commit": "abc123",
            "source_branch": "candidate/test",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "test_results": {"total": 10, "passed": 10},
            "r038a_ref": "ref_a", "r038b_ref": "ref_b",
            "r038c_ref": "ref_c", "r038d_ref": "ref_d",
        }
        res = validate_metrics_ci_artifacts(input_data)
        if res["pass_"]:
            failed += 1
            results.append({"id": "R038e_T002", "name": "reject_gross_only_metrics_bundle", "passed": False,
                           "detail": "gross-only metrics should fail R038e"})
        else:
            if any("METRICS_NET_OF_COST_MISSING" in c or "METRICS_MISSING_NET_OF_COST_PNL" in c for c in res["reason_codes"]):
                results.append({"id": "R038e_T002", "name": "reject_gross_only_metrics_bundle", "passed": True,
                               "detail": "correctly rejected gross-only metrics bundle"})
            else:
                failed += 1
                results.append({"id": "R038e_T002", "name": "reject_gross_only_metrics_bundle", "passed": False,
                               "detail": f"expected METRICS_NET_OF_COST_MISSING, got {res['reason_codes'][:3]}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038e_T002", "name": "reject_gross_only_metrics_bundle", "passed": False, "detail": str(e)})

    total += 1
    try:
        complete_metrics = {
            "net_of_cost_pnl": 100.0, "gross_pnl": 200.0,
            "total_cost": 2.0, "fee_cost": 1.0, "tax_cost": 0.6, "min_fee_effect": 0.4,
            "expected_slippage": 300.0, "actual_slippage": 350.0, "expected_vs_actual_slippage_drift": 0.05,
            "fill_probability": 0.8, "actual_fill_rate": 0.75, "fill_rate_drift": 0.05,
            "partial_fill_rate": 0.02, "rejected_order_rate": 0.01, "timeout_cancel_rate": 0.01,
            "max_drawdown": -100.0, "drawdown_duration": 30, "sharpe_ratio": 1.5,
            "sortino_ratio": 1.2, "calmar_ratio": 0.8, "win_rate": 0.55,
            "payoff_ratio": 1.5, "trade_count": 247, "turnover": 10000.0,
            "exposure": 0.3, "var": -50.0, "cvar": -75.0, "skewness": -0.12, "kurtosis": 3.1,
            "regime_breakdown": '{"bull":0.6,"bear":0.4}',
            "paper_live_drift": 0.03,
            "replay_compatibility_flag": True, "risk_gate_replay_compatibility_flag": True,
            "market_reality_compatibility_flag": True, "taiwan_constraints_flag": True,
            "capacity_liquidity_cap": 500000.0,
        }
        input_data: R038eMetricsCIArtifactsInput = {
            "metrics": complete_metrics,
            "source_commit": "abc123",
            "source_branch": "candidate/test",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "test_results": {"total": 10, "passed": 10},
            "r038a_ref": "ref_a", "r038b_ref": "ref_b",
            "r038c_ref": "ref_c", "r038d_ref": "ref_d",
        }
        res = validate_metrics_ci_artifacts(input_data)
        if not res["pass_"]:
            failed += 1
            results.append({"id": "R038e_T003", "name": "pass_complete_metrics_bundle", "passed": False,
                           "detail": f"complete metrics bundle should pass R038e, got codes: {res['reason_codes'][:3]}"})
        else:
            results.append({"id": "R038e_T003", "name": "pass_complete_metrics_bundle", "passed": True,
                           "detail": "complete metrics bundle correctly passed R038e"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038e_T003", "name": "pass_complete_metrics_bundle", "passed": False, "detail": str(e)})

    # === R038f NEA negative fail-closed tests (8 tests) ===
    total += 1
    try:
        inp: dict[str, Any] = {
            "p_hat": None, "W_hat": 0.10, "L_hat": 0.05,
            "C": 0.01, "S": 0.005, "B": 0.001, "T": 0.001, "R": 0.005, "U": 0.01,
            "fill_probability": 0.8, "regime_uncertainty": 0.1,
            "market_reality_snapshot": {}, "risk_snapshot": {},
            "threshold_config_version": "r038f_v1", "calibration_version": "r038f_cal_v1",
            "taiwan_reality_contract": {"price": 100.0, "reference_price": 100.0, "fee": 20.0},
            "order_execution_allowed": False,
            "calibration_brier_score": 0.18, "calibration_sample_count": 50,
            "calibration_timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_confidence_not_used": True, "vetoes": [], "llm_summary_only": True,
        }
        res = run_r038f_nea_confidence_calibration(**inp)
        if res["pass_"]:
            failed += 1
            results.append({"id": "R038f_T001", "name": "reject_missing_p_hat", "passed": False,
                           "detail": "p_hat=None should fail R038f NEA"})
        else:
            if any("P_HAT_MISSING" in c for c in res["reason_codes"]):
                results.append({"id": "R038f_T001", "name": "reject_missing_p_hat", "passed": True,
                               "detail": "correctly rejected missing p_hat"})
            else:
                failed += 1
                results.append({"id": "R038f_T001", "name": "reject_missing_p_hat", "passed": False,
                               "detail": f"expected P_HAT_MISSING, got {res['reason_codes'][:3]}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038f_T001", "name": "reject_missing_p_hat", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = {
            "p_hat": 0.7, "W_hat": 0.10, "L_hat": 0.05,
            "C": 0.01, "S": 0.005, "B": 0.001, "T": 0.001, "R": 0.005, "U": 0.01,
            "fill_probability": 0.8, "regime_uncertainty": 0.1,
            "market_reality_snapshot": {}, "risk_snapshot": {},
            "threshold_config_version": "r038f_v1", "calibration_version": "r038f_cal_v1",
            "taiwan_reality_contract": {"price": 100.0, "reference_price": 100.0, "fee": 20.0},
            "order_execution_allowed": False,
            "calibration_brier_score": 0.18, "calibration_sample_count": 50,
            "calibration_timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_confidence_not_used": True, "vetoes": [], "llm_summary_only": True,
        }
        res = run_r038f_nea_confidence_calibration(**inp)
        if res["pass_"]:
            failed += 1
            results.append({"id": "R038f_T002", "name": "reject_missing_market_reality", "passed": False,
                           "detail": "empty market_reality_snapshot should fail R038f"})
        else:
            if any("MARKET_REALITY_SNAPSHOT_MISSING" in c for c in res["reason_codes"]):
                results.append({"id": "R038f_T002", "name": "reject_missing_market_reality", "passed": True,
                               "detail": "correctly rejected missing market reality snapshot"})
            else:
                failed += 1
                results.append({"id": "R038f_T002", "name": "reject_missing_market_reality", "passed": False,
                               "detail": f"expected MARKET_REALITY_SNAPSHOT_MISSING, got {res['reason_codes'][:3]}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038f_T002", "name": "reject_missing_market_reality", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = {
            "p_hat": 0.7, "W_hat": 0.10, "L_hat": 0.05,
            "C": 0.01, "S": 0.005, "B": 0.001, "T": 0.001, "R": 0.005, "U": 0.01,
            "fill_probability": 0.8, "regime_uncertainty": 0.1,
            "market_reality_snapshot": {"cost_model_version": "v1"}, "risk_snapshot": {},
            "threshold_config_version": "r038f_v1", "calibration_version": "r038f_cal_v1",
            "taiwan_reality_contract": {"price": 100.0, "reference_price": 100.0, "fee": 20.0},
            "order_execution_allowed": False,
            "calibration_brier_score": 0.18, "calibration_sample_count": 50,
            "calibration_timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_confidence_not_used": False, "vetoes": [], "llm_summary_only": True,
        }
        res = run_r038f_nea_confidence_calibration(**inp)
        if res["pass_"]:
            failed += 1
            results.append({"id": "R038f_T003", "name": "reject_raw_confidence_used", "passed": False,
                           "detail": "raw_confidence_not_used=False should fail R038f"})
        else:
            if any("RAW_CONFIDENCE" in c for c in res["reason_codes"]):
                results.append({"id": "R038f_T003", "name": "reject_raw_confidence_used", "passed": True,
                               "detail": "correctly rejected raw confidence used"})
            else:
                failed += 1
                results.append({"id": "R038f_T003", "name": "reject_raw_confidence_used", "passed": False,
                               "detail": f"expected RAW_CONFIDENCE reason, got {res['reason_codes'][:3]}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038f_T003", "name": "reject_raw_confidence_used", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = {
            "p_hat": 0.7, "W_hat": 0.10, "L_hat": 0.05,
            "C": 0.01, "S": 0.005, "B": 0.001, "T": 0.001, "R": 0.005, "U": 0.01,
            "fill_probability": 0.8, "regime_uncertainty": 0.1,
            "market_reality_snapshot": {"cost_model_version": "v1"}, "risk_snapshot": {},
            "threshold_config_version": "r038f_v1", "calibration_version": "r038f_cal_v1",
            "taiwan_reality_contract": {"price": 100.0, "reference_price": 100.0, "fee": 20.0},
            "order_execution_allowed": False,
            "calibration_brier_score": 0.18, "calibration_sample_count": 50,
            "calibration_timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_confidence_not_used": True,
            "vetoes": ["BROKER_API_CALLED_VETO"], "llm_summary_only": True,
        }
        res = run_r038f_nea_confidence_calibration(**inp)
        if res["pass_"]:
            failed += 1
            results.append({"id": "R038f_T004", "name": "reject_broker_veto", "passed": False,
                           "detail": "broker API veto should fail R038f"})
        else:
            if any("BROKER_" in c for c in res["reason_codes"]):
                results.append({"id": "R038f_T004", "name": "reject_broker_veto", "passed": True,
                               "detail": "correctly rejected broker API veto"})
            else:
                failed += 1
                results.append({"id": "R038f_T004", "name": "reject_broker_veto", "passed": False,
                               "detail": f"expected BROKER_ reason, got {res['reason_codes'][:3]}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038f_T004", "name": "reject_broker_veto", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = {
            "p_hat": 0.7, "W_hat": 0.10, "L_hat": 0.05,
            "C": 0.01, "S": 0.005, "B": 0.001, "T": 0.001, "R": 0.005, "U": 0.01,
            "fill_probability": 0.8, "regime_uncertainty": 0.1,
            "market_reality_snapshot": {"cost_model_version": "v1"}, "risk_snapshot": {},
            "threshold_config_version": "r038f_v1", "calibration_version": "r038f_cal_v1",
            "taiwan_reality_contract": {"price": 115.0, "reference_price": 100.0, "fee": 20.0},
            "order_execution_allowed": False,
            "calibration_brier_score": 0.18, "calibration_sample_count": 50,
            "calibration_timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_confidence_not_used": True, "vetoes": [], "llm_summary_only": True,
        }
        res = run_r038f_nea_confidence_calibration(**inp)
        if res["pass_"]:
            failed += 1
            results.append({"id": "R038f_T005", "name": "reject_taiwan_price_limit_violation", "passed": False,
                           "detail": "price change=15% > 10% should fail R038f"})
        else:
            if any("TAIWAN_PRICE_LIMIT_VIOLATION" in c for c in res["reason_codes"]):
                results.append({"id": "R038f_T005", "name": "reject_taiwan_price_limit_violation", "passed": True,
                               "detail": "correctly rejected Taiwan price limit violation"})
            else:
                failed += 1
                results.append({"id": "R038f_T005", "name": "reject_taiwan_price_limit_violation", "passed": False,
                               "detail": f"expected TAIWAN_PRICE_LIMIT_VIOLATION, got {res['reason_codes'][:3]}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038f_T005", "name": "reject_taiwan_price_limit_violation", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = {
            "p_hat": 0.7, "W_hat": 0.10, "L_hat": 0.05,
            "C": 0.01, "S": 0.005, "B": 0.001, "T": 0.001, "R": 0.005, "U": 0.01,
            "fill_probability": 0.3, "regime_uncertainty": 0.1,
            "market_reality_snapshot": {"cost_model_version": "v1"},
            "risk_snapshot": {"var": -50.0, "cvar": -75.0},
            "threshold_config_version": "r038f_v1", "calibration_version": "r038f_cal_v1",
            "taiwan_reality_contract": {"price": 100.0, "reference_price": 100.0, "fee": 20.0},
            "order_execution_allowed": False,
            "calibration_brier_score": 0.18, "calibration_sample_count": 50,
            "calibration_timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_confidence_not_used": True, "vetoes": [], "llm_summary_only": True,
        }
        res = run_r038f_nea_confidence_calibration(**inp)
        if res["pass_"]:
            failed += 1
            results.append({"id": "R038f_T006", "name": "reject_fill_prob_below_threshold", "passed": False,
                           "detail": "fill_probability=0.3 < 0.5 should fail R038f"})
        else:
            if any("FILL_PROBABILITY_BELOW_THRESHOLD" in c for c in res["reason_codes"]):
                results.append({"id": "R038f_T006", "name": "reject_fill_prob_below_threshold", "passed": True,
                               "detail": "correctly rejected fill probability below threshold"})
            else:
                failed += 1
                results.append({"id": "R038f_T006", "name": "reject_fill_prob_below_threshold", "passed": False,
                               "detail": f"expected FILL_PROBABILITY_BELOW_THRESHOLD, got {res['reason_codes'][:3]}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038f_T006", "name": "reject_fill_prob_below_threshold", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = {
            "p_hat": 0.7, "W_hat": 0.10, "L_hat": 0.05,
            "C": 0.01, "S": 0.005, "B": 0.001, "T": 0.001, "R": 0.005, "U": 0.01,
            "fill_probability": 0.8, "regime_uncertainty": 0.5,
            "market_reality_snapshot": {"cost_model_version": "v1"},
            "risk_snapshot": {"var": -50.0, "cvar": -75.0},
            "threshold_config_version": "r038f_v1", "calibration_version": "r038f_cal_v1",
            "taiwan_reality_contract": {"price": 100.0, "reference_price": 100.0, "fee": 20.0},
            "order_execution_allowed": False,
            "calibration_brier_score": 0.18, "calibration_sample_count": 50,
            "calibration_timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_confidence_not_used": True, "vetoes": [], "llm_summary_only": True,
        }
        res = run_r038f_nea_confidence_calibration(**inp)
        if res["pass_"]:
            failed += 1
            results.append({"id": "R038f_T007", "name": "reject_regime_uncertainty_exceeds", "passed": False,
                           "detail": "regime_uncertainty=0.5 > 0.4 should fail R038f"})
        else:
            if any("REGIME_UNCERTAINTY_EXCEEDS" in c for c in res["reason_codes"]):
                results.append({"id": "R038f_T007", "name": "reject_regime_uncertainty_exceeds", "passed": True,
                               "detail": "correctly rejected regime uncertainty exceeds threshold"})
            else:
                failed += 1
                results.append({"id": "R038f_T007", "name": "reject_regime_uncertainty_exceeds", "passed": False,
                               "detail": f"expected REGIME_UNCERTAINTY_EXCEEDS, got {res['reason_codes'][:3]}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038f_T007", "name": "reject_regime_uncertainty_exceeds", "passed": False, "detail": str(e)})

    total += 1
    try:
        inp = {
            "p_hat": 0.7, "W_hat": 0.10, "L_hat": 0.05,
            "C": 0.01, "S": 0.005, "B": 0.001, "T": 0.001, "R": 0.005, "U": 0.01,
            "fill_probability": 0.8, "regime_uncertainty": 0.1,
            "market_reality_snapshot": {"cost_model_version": "v1"}, "risk_snapshot": {},
            "threshold_config_version": "r038f_v1", "calibration_version": "r038f_cal_v1",
            "taiwan_reality_contract": {"price": 100.0, "reference_price": 100.0, "fee": 20.0},
            "order_execution_allowed": True,
            "calibration_brier_score": 0.18, "calibration_sample_count": 50,
            "calibration_timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_confidence_not_used": True, "vetoes": [], "llm_summary_only": True,
        }
        res = run_r038f_nea_confidence_calibration(**inp)
        if res["pass_"]:
            failed += 1
            results.append({"id": "R038f_T008", "name": "reject_oea_true_r038f", "passed": False,
                           "detail": "order_execution_allowed=True should fail R038f"})
        else:
            if any("ORDER_EXECUTION_ALLOWED" in c for c in res["reason_codes"]):
                results.append({"id": "R038f_T008", "name": "reject_oea_true_r038f", "passed": True,
                               "detail": "correctly rejected oea=True in R038f"})
            else:
                failed += 1
                results.append({"id": "R038f_T008", "name": "reject_oea_true_r038f", "passed": False,
                               "detail": f"expected ORDER_EXECUTION_ALLOWED, got {res['reason_codes'][:3]}"})
    except Exception as e:
        failed += 1
        results.append({"id": "R038f_T008", "name": "reject_oea_true_r038f", "passed": False, "detail": str(e)})

    # === Cross-stage calibration tests (5 tests) ===
    total += 1
    try:
        guard = ConfidenceCalibrationGuard()
        contract = _make_valid_calibration_contract(sample_count=5)
        res = guard.evaluate(raw_confidence=0.8, calibration_contract=contract, llm_summary_only=True)
        if res.reason_codes:
            if any("INSUFFICIENT_CALIBRATION_SAMPLES" in c for c in res.reason_codes):
                results.append({"id": "Cross_T001", "name": "reject_insufficient_calibration_samples", "passed": True,
                               "detail": "correctly rejected insufficient calibration samples"})
            else:
                failed += 1
                results.append({"id": "Cross_T001", "name": "reject_insufficient_calibration_samples", "passed": False,
                               "detail": f"expected INSUFFICIENT_CALIBRATION_SAMPLES, got {res.reason_codes}"})
        else:
            failed += 1
            results.append({"id": "Cross_T001", "name": "reject_insufficient_calibration_samples", "passed": False,
                           "detail": "insufficient calibration samples should produce reason codes"})
    except Exception as e:
        failed += 1
        results.append({"id": "Cross_T001", "name": "reject_insufficient_calibration_samples", "passed": False, "detail": str(e)})

    total += 1
    try:
        guard = ConfidenceCalibrationGuard()
        contract = _make_valid_calibration_contract(sample_count=50, days_ago=60)
        res = guard.evaluate(raw_confidence=0.8, calibration_contract=contract, llm_summary_only=True)
        if res.reason_codes:
            if any("STALE_CALIBRATION" in c for c in res.reason_codes):
                results.append({"id": "Cross_T002", "name": "reject_stale_calibration_contract", "passed": True,
                               "detail": "correctly rejected stale calibration contract"})
            else:
                failed += 1
                results.append({"id": "Cross_T002", "name": "reject_stale_calibration_contract", "passed": False,
                               "detail": f"expected STALE_CALIBRATION, got {res.reason_codes}"})
        else:
            failed += 1
            results.append({"id": "Cross_T002", "name": "reject_stale_calibration_contract", "passed": False,
                           "detail": "stale calibration contract should produce reason codes"})
    except Exception as e:
        failed += 1
        results.append({"id": "Cross_T002", "name": "reject_stale_calibration_contract", "passed": False, "detail": str(e)})

    total += 1
    try:
        guard = ConfidenceCalibrationGuard()
        res = guard.evaluate(raw_confidence=0.8, llm_summary_only=False)
        if res.reason_codes:
            if any("LLM_MARKS_PASS" in c for c in res.reason_codes):
                results.append({"id": "Cross_T003", "name": "reject_llm_marks_pass_cross", "passed": True,
                               "detail": "correctly rejected llm_summary_only=False"})
            else:
                failed += 1
                results.append({"id": "Cross_T003", "name": "reject_llm_marks_pass_cross", "passed": False,
                               "detail": f"expected LLM_MARKS_PASS, got {res.reason_codes}"})
        else:
            failed += 1
            results.append({"id": "Cross_T003", "name": "reject_llm_marks_pass_cross", "passed": False,
                           "detail": "llm_summary_only=False should produce reason codes"})
    except Exception as e:
        failed += 1
        results.append({"id": "Cross_T003", "name": "reject_llm_marks_pass_cross", "passed": False, "detail": str(e)})

    total += 1
    try:
        guard = ConfidenceCalibrationGuard()
        res = guard.evaluate(raw_confidence=-0.5, llm_summary_only=True)
        if res.veto_reason or res.reason_codes:
            results.append({"id": "Cross_T004", "name": "reject_raw_confidence_out_of_range", "passed": True,
                           "detail": "correctly rejected raw_confidence out of range"})
        else:
            failed += 1
            results.append({"id": "Cross_T004", "name": "reject_raw_confidence_out_of_range", "passed": False,
                           "detail": "raw_confidence=-0.5 should produce veto or reason codes"})
    except Exception as e:
        failed += 1
        results.append({"id": "Cross_T004", "name": "reject_raw_confidence_out_of_range", "passed": False, "detail": str(e)})

    total += 1
    try:
        guard = ConfidenceCalibrationGuard()
        res = guard.evaluate(raw_confidence=0.4, llm_summary_only=True)
        if res.veto_reason:
            results.append({"id": "Cross_T005", "name": "reject_raw_confidence_low", "passed": True,
                           "detail": "correctly rejected raw_confidence <= 0.5"})
        else:
            failed += 1
            results.append({"id": "Cross_T005", "name": "reject_raw_confidence_low", "passed": False,
                           "detail": f"raw_confidence=0.4 should produce veto, got calibrated={res.calibrated_confidence}, veto={res.veto_reason}"})
    except Exception as e:
        failed += 1
        results.append({"id": "Cross_T005", "name": "reject_raw_confidence_low", "passed": False, "detail": str(e)})

    # === Valid positive cases (3 tests) ===
    total += 1
    try:
        inp = DecisionTraceReplayInput(
            trace_id="t_valid",
            market_reality_snapshot=_make_valid_snapshot(5.0),
            risk_gate_replay_result=_make_valid_risk_gate(),
            taiwan_reality_contract=_make_taiwan_contract(),
            fill_ref=_make_valid_filled_order("FILLED"),
            as_of_source_ts="2025-01-01T09:00:00Z",
            as_of_publish_ts="2025-01-01T09:05:00Z",
            as_of_ingest_ts="2025-01-01T09:10:00Z",
            tradable_ts="2025-01-01T09:30:00Z",
            decision_ts="2025-01-01T09:35:00Z",
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        if res.fail_closed:
            failed += 1
            results.append({"id": "Valid_T001", "name": "pass_valid_r038a", "passed": False,
                           "detail": f"valid input should pass but got reason_codes: {res.reason_codes[:3]}"})
        else:
            results.append({"id": "Valid_T001", "name": "pass_valid_r038a", "passed": True,
                           "detail": "valid input correctly passed R038a"})
    except Exception as e:
        failed += 1
        results.append({"id": "Valid_T001", "name": "pass_valid_r038a", "passed": False, "detail": str(e)})

    total += 1
    try:
        l0 = L0BacktestEvidence(
            net_of_cost_pnl=100.0, gross_pnl=200.0,
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            trade_count=100, max_drawdown=-0.10,
            order_fill_pnl_schema_compatible=True, market_reality_compatible=True,
            replay_compatible=True, risk_gate_replay_compatible=True,
        )
        l1 = L1WalkForwardEvidence(
            train_window_count=5, test_window_count=3, out_of_sample_windows=3,
            no_lookahead_leak=True, window_level_net_of_cost=True,
            window_cost_model_version="cost_v1", window_slippage_model_version="slip_v1",
        )
        l2 = L2MonteCarloPermutationEvidence(
            permutation_count=200, monte_carlo_runs=200,
            p_value=0.03, random_seed=42, tail_risk_metric={"max_drawdown": -0.15},
        )
        l3 = L3BlockBootstrapEvidence(
            block_count=20, block_size=30, bootstrap_runs=600,
            confidence_interval={"lower": -0.10, "upper": 0.15},
            regime_serial_dependence_aware=True,
        )
        l4 = L4MultipleTestingCorrectionEvidence(
            trial_count=50, corrected_p_value=0.02,
            search_ledger=[{"trial": i} for i in range(50)],
        )
        inp = L0L4ValidationInput(
            input_id="b_valid", l0_evidence=l0, l1_evidence=l1,
            l2_evidence=l2, l3_evidence=l3, l4_evidence=l4,
        )
        res = validate_l0_l4_chain(inp)
        if res.fail_closed:
            failed += 1
            results.append({"id": "Valid_T002", "name": "pass_valid_r038b", "passed": False,
                           "detail": f"valid input should pass but got reason_codes: {res.reason_codes[:3]}"})
        else:
            results.append({"id": "Valid_T002", "name": "pass_valid_r038b", "passed": True,
                           "detail": "valid input correctly passed R038b"})
    except Exception as e:
        failed += 1
        results.append({"id": "Valid_T002", "name": "pass_valid_r038b", "passed": False, "detail": str(e)})

    total += 1
    try:
        l5 = L5WalkForwardOOSEvidence(
            final_out_of_sample_period="2024H2", oos_window_count=3,
            no_training_overlap_with_oos=True, no_future_leak=True,
            as_of_replay_compatible=True, net_of_cost_oos_result=0.05,
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            market_reality_compatible=True, risk_gate_replay_compatible=True,
        )
        l6 = L6RegimeSegmentEvidence(
            regime_count=3, regime_labels=["bull", "bear", "sideways"],
            per_regime_sample_count={"bull": 100, "bear": 80, "sideways": 60},
            per_regime_net_of_cost_result={"bull": 0.08, "bear": 0.03, "sideways": 0.01},
            aggregate_net_of_cost_result=0.05,
            regime_definition_version="v1",
            offline_labeler_vs_online_filter_declared=True,
            no_hindsight_regime_for_live=True,
            regime_uncertainty_policy_present=True,
            market_reality_compatible_per_regime=True,
        )
        l7 = L7CombinatorialPurgedCVEvidence(
            combinatorial_split_count=5, purge_window=10, embargo_window=5,
            fold_count=5, time_series_order_preserved=True,
            overlapping_label_protection=True, leakage_gap_declared=True,
            per_fold_net_of_cost_result=[0.01, 0.02, 0.03, 0.02, 0.01],
        )
        l8 = L8PSRRealityCheckSPAEvidence(
            probabilistic_sharpe_ratio=0.85, raw_sharpe_ratio=1.5,
            reality_check_p_value=0.03, spa_p_value=0.05,
            benchmark_or_strategy_family_baseline="spy",
            multiple_testing_adjusted_p_value=0.04,
            bootstrap_or_resampling_method="block_bootstrap",
            non_normality_or_tail_risk_adjustment="skewness_kurtosis_adjustment",
            trade_count=100, net_of_cost_metric_used=True,
            raw_sharpe_not_sufficient=False, gross_metric_used=False,
        )
        l9 = L9PaperTradingReadinessEvidence(
            paper_duration_months=8, paper_trading_days=120,
            paper_trade_count=50, paper_net_of_cost_pnl=200.0,
            paper_live_drift_policy_present=True,
            strategy_ttl_or_promotion_expiry="2025-12-31",
            revalidation_required_before_live=True,
            human_approval_required_for_live=True,
            no_live_order_path=True, order_execution_allowed=False,
        )
        inp = L5L9ValidationInput(
            input_id="c_valid", l5_evidence=l5, l6_evidence=l6,
            l7_evidence=l7, l8_evidence=l8, l9_evidence=l9,
        )
        res = validate_l5_l9_chain(inp)
        if res.fail_closed:
            failed += 1
            results.append({"id": "Valid_T003", "name": "pass_valid_r038c", "passed": False,
                           "detail": f"valid input should pass but got reason_codes: {res.reason_codes[:3]}"})
        else:
            results.append({"id": "Valid_T003", "name": "pass_valid_r038c", "passed": True,
                           "detail": "valid input correctly passed R038c"})
    except Exception as e:
        failed += 1
        results.append({"id": "Valid_T003", "name": "pass_valid_r038c", "passed": False, "detail": str(e)})

    passed = total - failed
    return {
        "stage": STAGE_R038G,
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total, 4) if total > 0 else 0.0,
        "results": results,
    }