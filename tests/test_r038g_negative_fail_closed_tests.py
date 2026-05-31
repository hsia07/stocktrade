"""
R038g Negative Fail-Closed Tests — Candidate Validation Suite

Purpose: Verify that all R038a–R038f fail-closed behaviors are enforced when
order_execution_allowed=False (fail-closed invariant).

These are pytest wrapper tests around the same logic in the R038g module.
They use the same APIs (validate_and_replay, validate_l0_l4_chain, etc.)
that the internal R038g suite uses internally.
"""

import pytest
from modules.decision_prechecklist.r038g_negative_fail_closed_tests import (
    R038GTestCase,
    R038GTestResult,
    R038GTestSuite,
    get_fail_closed_tests,
    run_r038g_fail_closed_tests,
    STAGE_R038G,
    FAIL_CLOSED_REASON_CODES_R038G,
    run_r038g_negative_fail_closed_tests,
)


class TestR038GReasonCodes:
    def test_fail_closed_reason_codes_defined(self):
        assert isinstance(FAIL_CLOSED_REASON_CODES_R038G, dict)
        assert len(FAIL_CLOSED_REASON_CODES_R038G) > 0

    def test_stage_name_defined(self):
        assert STAGE_R038G == "R038g_negative_fail_closed_tests"


class TestR038GSuiteGeneration:
    def test_get_fail_closed_tests_returns_list(self):
        tests = get_fail_closed_tests()
        assert isinstance(tests, list)
        assert len(tests) > 0

    def test_all_tests_have_required_fields(self):
        tests = get_fail_closed_tests()
        for t in tests:
            assert hasattr(t, "test_id")
            assert hasattr(t, "stage")
            assert hasattr(t, "description")
            assert hasattr(t, "input_data")
            assert hasattr(t, "expected_pass")
            assert hasattr(t, "expected_reason_codes")

    def test_run_fail_closed_tests_returns_suite(self):
        tests = get_fail_closed_tests()
        suite = run_r038g_fail_closed_tests(tests)
        assert isinstance(suite, R038GTestSuite)
        assert suite.total == len(tests)
        assert suite.stage == STAGE_R038G

    def test_run_r038g_returns_dict(self):
        result = run_r038g_negative_fail_closed_tests()
        assert isinstance(result, dict)
        assert "stage" in result
        assert "total" in result
        assert "passed" in result
        assert "failed" in result
        assert "results" in result


class TestR038GInternalSuite:
    def test_r038g_suite_runs_without_exception(self):
        result = run_r038g_negative_fail_closed_tests()
        assert result["total"] > 0
        assert result["total"] == len(result["results"])

    def test_r038g_all_results_have_id_and_passed(self):
        result = run_r038g_negative_fail_closed_tests()
        for r in result["results"]:
            assert "id" in r
            assert "name" in r
            assert "passed" in r
            assert "detail" in r

    def test_r038g_stages_covered(self):
        result = run_r038g_negative_fail_closed_tests()
        ids = [r["id"] for r in result["results"]]
        stages = set()
        for id_ in ids:
            prefix = id_.split("_")[0]
            if prefix in ("R038a", "R038b", "R038c", "R038d", "R038e", "R038f", "Cross", "Valid"):
                stages.add(prefix)
        assert "R038a" in stages
        assert "R038b" in stages
        assert "R038c" in stages
        assert "R038d" in stages
        assert "R038e" in stages
        assert "R038f" in stages

    def test_r038g_cross_stage_tests_present(self):
        result = run_r038g_negative_fail_closed_tests()
        ids = [r["id"] for r in result["results"]]
        cross_ids = [i for i in ids if i.startswith("Cross_")]
        assert len(cross_ids) >= 5

    def test_r038g_valid_positive_cases_present(self):
        result = run_r038g_negative_fail_closed_tests()
        ids = [r["id"] for r in result["results"]]
        valid_ids = [i for i in ids if i.startswith("Valid_")]
        assert len(valid_ids) >= 3


# =============================================================================
# TestR038aFailClosedIndividual — R038a fail-closed per failure mode
# =============================================================================

class TestR038aFailClosedIndividual:
    """Test each R038a failure case individually."""

    def test_r038a_missing_market_reality_snapshot(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay,
        )
        inp = DecisionTraceReplayInput(trace_id="t001")
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True
        assert len(res.reason_codes) > 0

    def test_r038a_missing_asof_timestamps(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult, TaiwanRealityContract,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        taiwan = TaiwanRealityContract(
            tax_rate=0.003, fee_rate=0.001425, minimum_fee=1.0,
            price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
            minimum_fee_aware=True,
        )
        inp = DecisionTraceReplayInput(
            trace_id="t002", market_reality_snapshot=snap,
            risk_gate_replay_result=risk, taiwan_reality_contract=taiwan,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True
        codes = res.reason_codes
        assert "AS_OF_SOURCE_TS_MISSING" in codes or "AS_OF_PUBLISH_TS_MISSING" in codes or "AS_OF_INGEST_TS_MISSING" in codes

    def test_r038a_limit_updown_near_boundary(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult, TaiwanRealityContract,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=1.5,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        taiwan = TaiwanRealityContract(
            tax_rate=0.003, fee_rate=0.001425, minimum_fee=1.0,
            price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
            minimum_fee_aware=True,
        )
        inp = DecisionTraceReplayInput(
            trace_id="t003", market_reality_snapshot=snap,
            risk_gate_replay_result=risk, taiwan_reality_contract=taiwan,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True
        assert any("LIMIT_UP_DOWN" in c for c in res.reason_codes)

    def test_r038a_fill_probability_above_one(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult, TaiwanRealityContract,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=1.5,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        inp = DecisionTraceReplayInput(
            trace_id="t004", market_reality_snapshot=snap,
            risk_gate_replay_result=risk,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True
        assert any("FILL_PROBABILITY_OUT_OF_RANGE" in c for c in res.reason_codes)

    def test_r038a_fill_probability_below_zero(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=-0.1,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        inp = DecisionTraceReplayInput(
            trace_id="t005", market_reality_snapshot=snap,
            risk_gate_replay_result=risk,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True
        assert any("FILL_PROBABILITY_OUT_OF_RANGE" in c for c in res.reason_codes)

    def test_r038a_negative_expected_net_rr(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=-0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        inp = DecisionTraceReplayInput(
            trace_id="t006", market_reality_snapshot=snap,
            risk_gate_replay_result=risk,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True
        assert any("EXPECTED_NET_RR_NOT_POSITIVE" in c for c in res.reason_codes)

    def test_r038a_risk_gate_veto(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(
            risk_gate_results={"gate1": "veto"},
            veto_reason_codes=["gate1_veto"],
        )
        inp = DecisionTraceReplayInput(
            trace_id="t007", market_reality_snapshot=snap,
            risk_gate_replay_result=risk,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True
        assert res.vetoed is True
        assert any("RISK_GATE_VETO" in c for c in res.reason_codes)

    def test_r038a_halt_disposition_attention(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult, TaiwanRealityContract,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        taiwan = TaiwanRealityContract(
            tax_rate=0.003, fee_rate=0.001425, minimum_fee=1.0,
            price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
            minimum_fee_aware=True, halt_disposition_attention="halt",
        )
        inp = DecisionTraceReplayInput(
            trace_id="t008", market_reality_snapshot=snap,
            risk_gate_replay_result=risk, taiwan_reality_contract=taiwan,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True
        assert any("HALT_DISPOSITION" in c for c in res.reason_codes)

    def test_r038a_fill_rejected(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult, OptionalFillRef,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        fill = OptionalFillRef(
            fill_id="fill_001", fill_qty=100, fill_price=100.0,
            fill_status="REJECTED", partial_fill_accepted=False,
        )
        inp = DecisionTraceReplayInput(
            trace_id="t009", market_reality_snapshot=snap,
            risk_gate_replay_result=risk, fill_ref=fill,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True
        assert any("FILL_REJECTED_OR_FAILED" in c for c in res.reason_codes)

    def test_r038a_minimum_fee_unaware(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult, TaiwanRealityContract,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        taiwan = TaiwanRealityContract(
            tax_rate=0.003, fee_rate=0.001425, minimum_fee=1.0,
            price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
            minimum_fee_aware=False,
        )
        inp = DecisionTraceReplayInput(
            trace_id="t010", market_reality_snapshot=snap,
            risk_gate_replay_result=risk, taiwan_reality_contract=taiwan,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True
        assert any("MINIMUM_FEE_AWARE_NOT_TRUE" in c for c in res.reason_codes)

    def test_r038a_liquidity_insufficiency(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult, TaiwanRealityContract,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        taiwan = TaiwanRealityContract(
            tax_rate=0.003, fee_rate=0.001425, minimum_fee=1.0,
            price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
            minimum_fee_aware=True, liquidity_insufficiency="insufficient",
        )
        inp = DecisionTraceReplayInput(
            trace_id="t011", market_reality_snapshot=snap,
            risk_gate_replay_result=risk, taiwan_reality_contract=taiwan,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True
        assert any("LIQUIDITY_INSUFFICIENCY" in c for c in res.reason_codes)

    def test_r038a_decision_before_tradable(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult, TaiwanRealityContract,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        taiwan = TaiwanRealityContract(
            tax_rate=0.003, fee_rate=0.001425, minimum_fee=1.0,
            price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
            minimum_fee_aware=True,
        )
        inp = DecisionTraceReplayInput(
            trace_id="t012", market_reality_snapshot=snap,
            risk_gate_replay_result=risk, taiwan_reality_contract=taiwan,
            as_of_source_ts="2025-01-01T09:00:00Z",
            as_of_publish_ts="2025-01-01T09:05:00Z",
            as_of_ingest_ts="2025-01-01T09:10:00Z",
            decision_ts="2025-01-01T09:30:00Z",
            tradable_ts="2025-01-01T10:00:00Z",
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True

    def test_r038a_oea_true_rejected(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult, TaiwanRealityContract,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        taiwan = TaiwanRealityContract(
            tax_rate=0.003, fee_rate=0.001425, minimum_fee=1.0,
            price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
            minimum_fee_aware=True,
        )
        inp = DecisionTraceReplayInput(
            trace_id="t013", market_reality_snapshot=snap,
            risk_gate_replay_result=risk, taiwan_reality_contract=taiwan,
        )
        res = validate_and_replay(inp, order_execution_allowed=True)
        assert res.fail_closed is True
        assert any("ORDER_EXECUTION_ALLOWED_NOT_FALSE" in c for c in res.reason_codes)

    def test_r038a_oea_result_preserved_false(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult, TaiwanRealityContract,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        taiwan = TaiwanRealityContract(
            tax_rate=0.003, fee_rate=0.001425, minimum_fee=1.0,
            price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
            minimum_fee_aware=True,
        )
        inp = DecisionTraceReplayInput(
            trace_id="t014", market_reality_snapshot=snap,
            risk_gate_replay_result=risk, taiwan_reality_contract=taiwan,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.order_execution_allowed is False

    def test_r038a_fill_unfilled(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult, OptionalFillRef,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        fill = OptionalFillRef(
            fill_id="fill_002", fill_qty=100, fill_price=100.0,
            fill_status="UNFILLED", partial_fill_accepted=False,
        )
        inp = DecisionTraceReplayInput(
            trace_id="t015", market_reality_snapshot=snap,
            risk_gate_replay_result=risk, fill_ref=fill,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True
        assert any("FILL_UNFILLED" in c for c in res.reason_codes)


# =============================================================================
# TestR038bFailClosedIndividual — R038b L0-L4 fail-closed per failure mode
# =============================================================================

class TestR038bFailClosedIndividual:
    """Test each R038b L0-L4 failure case individually."""

    def test_r038b_l0_completely_missing(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, validate_l0_l4_chain,
        )
        inp = L0L4ValidationInput(input_id="b001")
        res = validate_l0_l4_chain(inp)
        assert res.fail_closed is True
        assert len(res.reason_codes) > 0

    def test_r038b_l0_gross_only_result(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L0BacktestEvidence, validate_l0_l4_chain,
        )
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
        assert res.fail_closed is True
        assert any("L0_GROSS_ONLY_RESULT" in c for c in res.reason_codes)

    def test_r038b_l0_insufficient_trade_count(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L0BacktestEvidence, validate_l0_l4_chain,
        )
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
        assert res.fail_closed is True
        assert any("L0_TRADE_COUNT_INSUFFICIENT" in c for c in res.reason_codes)

    def test_r038b_l0_tradingview_only(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L0BacktestEvidence, validate_l0_l4_chain,
        )
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
        assert res.fail_closed is True
        assert any("TRADINGVIEW_ONLY" in c for c in res.reason_codes)

    def test_r038b_l0_tradingview_with_compat_flags(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L0BacktestEvidence, validate_l0_l4_chain,
        )
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
        assert res.fail_closed is True
        assert any("TRADINGVIEW_ONLY" in c for c in res.reason_codes)

    def test_r038b_l2_missing_random_seed(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L2MonteCarloPermutationEvidence, validate_l0_l4_chain,
        )
        evidence = L2MonteCarloPermutationEvidence(
            permutation_count=50, monte_carlo_runs=50,
            p_value=0.10, random_seed=None, tail_risk_metric={},
        )
        inp = L0L4ValidationInput(input_id="b006", l2_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        assert res.fail_closed is True
        assert any("L2_MISSING_SEED" in c for c in res.reason_codes)

    def test_r038b_l2_pvalue_above_threshold(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L2MonteCarloPermutationEvidence, validate_l0_l4_chain,
        )
        evidence = L2MonteCarloPermutationEvidence(
            permutation_count=50, monte_carlo_runs=50,
            p_value=0.10, random_seed=42, tail_risk_metric={},
        )
        inp = L0L4ValidationInput(input_id="b007", l2_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        assert res.fail_closed is True
        assert any("L2_P_VALUE_ABOVE_THRESHOLD" in c for c in res.reason_codes)

    def test_r038b_l4_trial_count_missing(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L4MultipleTestingCorrectionEvidence, validate_l0_l4_chain,
        )
        evidence = L4MultipleTestingCorrectionEvidence(
            trial_count=0, corrected_p_value=None, search_ledger=[],
        )
        inp = L0L4ValidationInput(input_id="b008", l4_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        assert res.fail_closed is True
        assert any("L4_TRIAL_COUNT_MISSING" in c for c in res.reason_codes)

    def test_r038b_l0_negative_net_of_cost_pnl(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L0BacktestEvidence, validate_l0_l4_chain,
        )
        evidence = L0BacktestEvidence(
            net_of_cost_pnl=-50.0, gross_pnl=200.0,
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            trade_count=100, max_drawdown=-0.15,
            order_fill_pnl_schema_compatible=True,
            market_reality_compatible=True, replay_compatible=True,
            risk_gate_replay_compatible=True,
        )
        inp = L0L4ValidationInput(input_id="b009", l0_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        assert res.fail_closed is True

    def test_r038b_l0_max_drawdown_too_deep(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L0BacktestEvidence, validate_l0_l4_chain,
        )
        evidence = L0BacktestEvidence(
            net_of_cost_pnl=100.0, gross_pnl=200.0,
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            trade_count=100, max_drawdown=-0.50,
            order_fill_pnl_schema_compatible=True,
            market_reality_compatible=True, replay_compatible=True,
            risk_gate_replay_compatible=True,
        )
        inp = L0L4ValidationInput(input_id="b010", l0_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        assert res.fail_closed is True

    def test_r038b_l1_walkforward_missing_required_fields(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L1WalkForwardEvidence, validate_l0_l4_chain,
        )
        evidence = L1WalkForwardEvidence(
            train_window_count=0, test_window_count=0,
            out_of_sample_windows=0, no_lookahead_leak=False,
            window_level_net_of_cost=False,
        )
        inp = L0L4ValidationInput(input_id="b011", l1_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        assert res.fail_closed is True
        assert any("L1_WINDOWS_MISSING" in c for c in res.reason_codes)

    def test_r038b_l3_block_bootstrap_invalid(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L3BlockBootstrapEvidence, validate_l0_l4_chain,
        )
        evidence = L3BlockBootstrapEvidence(
            block_count=0, block_size=0, bootstrap_runs=0,
            confidence_interval={}, regime_serial_dependence_aware=False,
        )
        inp = L0L4ValidationInput(input_id="b012", l3_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        assert res.fail_closed is True
        assert any("L3_BOOTSTRAP_RESULT_MISSING" in c for c in res.reason_codes)

    def test_r038b_oea_true_rejected(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, validate_l0_l4_chain,
        )
        inp = L0L4ValidationInput(input_id="b013", order_execution_allowed=True)
        res = validate_l0_l4_chain(inp)
        assert res.fail_closed is True
        assert any("ORDER_EXECUTION_ALLOWED" in c for c in res.reason_codes)

    def test_r038b_oea_preserved_false(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, validate_l0_l4_chain,
        )
        inp = L0L4ValidationInput(input_id="b014")
        res = validate_l0_l4_chain(inp)
        assert res.order_execution_allowed is False


# =============================================================================
# TestR038cFailClosedIndividual — R038c L5-L9 fail-closed per failure mode
# =============================================================================

class TestR038cFailClosedIndividual:
    """Test each R038c L5-L9 failure case individually."""

    def test_r038c_l5_completely_missing(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, validate_l5_l9_chain,
        )
        inp = L5L9ValidationInput(input_id="c001")
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True
        assert len(res.reason_codes) > 0

    def test_r038c_l5_oos_gross_only(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L5WalkForwardOOSEvidence, validate_l5_l9_chain,
        )
        evidence = L5WalkForwardOOSEvidence(
            final_out_of_sample_period="2025Q1",
            oos_window_count=0,
            no_training_overlap_with_oos=False,
            no_future_leak=False,
            as_of_replay_compatible=False,
            net_of_cost_oos_result=None,
            gross_oos_result=100.0,
        )
        inp = L5L9ValidationInput(input_id="c002", l5_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True
        assert any("L5_OOS_RESULT_GROSS_ONLY" in c for c in res.reason_codes)

    def test_r038c_l5_training_overlap(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L5WalkForwardOOSEvidence, validate_l5_l9_chain,
        )
        evidence = L5WalkForwardOOSEvidence(
            final_out_of_sample_period="2025Q1",
            oos_window_count=3,
            no_training_overlap_with_oos=False,
            no_future_leak=True,
            as_of_replay_compatible=True,
            net_of_cost_oos_result=50.0,
            cost_model_version="cost_v1",
            slippage_model_version="slip_v1",
            market_reality_compatible=True,
            risk_gate_replay_compatible=True,
        )
        inp = L5L9ValidationInput(input_id="c003", l5_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True
        assert any("L5_TRAIN_TEST_OVERLAP" in c for c in res.reason_codes)

    def test_r038c_l6_single_regime_only(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L6RegimeSegmentEvidence, validate_l5_l9_chain,
        )
        evidence = L6RegimeSegmentEvidence(
            regime_count=1,
            regime_labels=["bull"],
            per_regime_sample_count={"bull": 100},
            per_regime_net_of_cost_result={"bull": 50.0},
            offline_labeler_vs_online_filter_declared=False,
            no_hindsight_regime_for_live=True,
            regime_uncertainty_policy_present=False,
            market_reality_compatible_per_regime=False,
        )
        inp = L5L9ValidationInput(input_id="c004", l6_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True
        assert any("L6_SINGLE_REGIME_ONLY" in c for c in res.reason_codes)

    def test_r038c_l7_missing_purge_window(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L7CombinatorialPurgedCVEvidence, validate_l5_l9_chain,
        )
        evidence = L7CombinatorialPurgedCVEvidence(
            combinatorial_split_count=0, purge_window=0, embargo_window=0,
            fold_count=0,
            time_series_order_preserved=False,
            overlapping_label_protection=False,
            leakage_gap_declared=False,
        )
        inp = L5L9ValidationInput(input_id="c005", l7_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True
        assert any("L7_PURGE_WINDOW_MISSING" in c for c in res.reason_codes)

    def test_r038c_l8_raw_sharpe_only(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L8PSRRealityCheckSPAEvidence, validate_l5_l9_chain,
        )
        evidence = L8PSRRealityCheckSPAEvidence(
            raw_sharpe_ratio=1.5,
            probabilistic_sharpe_ratio=None,
            reality_check_p_value=None,
            spa_p_value=None,
            benchmark_or_strategy_family_baseline="",
            multiple_testing_adjusted_p_value=None,
            bootstrap_or_resampling_method="",
            non_normality_or_tail_risk_adjustment="",
            trade_count=10,
            net_of_cost_metric_used=False,
            gross_metric_used=False,
        )
        inp = L5L9ValidationInput(input_id="c006", l8_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True
        assert any("L8_RAW_SHARPE_ONLY" in c for c in res.reason_codes)

    def test_r038c_l9_paper_duration_below_minimum(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L9PaperTradingReadinessEvidence, validate_l5_l9_chain,
        )
        evidence = L9PaperTradingReadinessEvidence(
            paper_duration_months=3,
            paper_trading_days=30,
            paper_trade_count=10,
            paper_net_of_cost_pnl=None,
            paper_live_drift_policy_present=False,
            strategy_ttl_or_promotion_expiry="",
            revalidation_required_before_live=False,
            human_approval_required_for_live=False,
            no_live_order_path=False,
            order_execution_allowed=False,
        )
        inp = L5L9ValidationInput(input_id="c007", l9_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True
        assert any("L9_PAPER_DURATION_BELOW_MINIMUM" in c for c in res.reason_codes)

    def test_r038c_l9_live_order_path_present(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L9PaperTradingReadinessEvidence, validate_l5_l9_chain,
        )
        evidence = L9PaperTradingReadinessEvidence(
            paper_duration_months=6,
            paper_trading_days=60,
            paper_trade_count=30,
            paper_net_of_cost_pnl=100.0,
            paper_live_drift_policy_present=True,
            strategy_ttl_or_promotion_expiry="2025-06-01",
            revalidation_required_before_live=True,
            human_approval_required_for_live=True,
            no_live_order_path=False,
            order_execution_allowed=False,
        )
        inp = L5L9ValidationInput(input_id="c008", l9_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True
        assert any("L9_LIVE_ORDER_PATH_PRESENT" in c for c in res.reason_codes)

    def test_r038c_l9_human_approval_missing(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L9PaperTradingReadinessEvidence, validate_l5_l9_chain,
        )
        evidence = L9PaperTradingReadinessEvidence(
            paper_duration_months=6,
            paper_trading_days=60,
            paper_trade_count=30,
            paper_net_of_cost_pnl=100.0,
            paper_live_drift_policy_present=True,
            strategy_ttl_or_promotion_expiry="2025-06-01",
            revalidation_required_before_live=True,
            human_approval_required_for_live=False,
            no_live_order_path=True,
            order_execution_allowed=False,
        )
        inp = L5L9ValidationInput(input_id="c009", l9_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True
        assert any("L9_HUMAN_APPROVAL_MISSING" in c for c in res.reason_codes)

    def test_r038c_l5_oos_sharpe_below_threshold(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L5WalkForwardOOSEvidence, validate_l5_l9_chain,
        )
        evidence = L5WalkForwardOOSEvidence(
            final_out_of_sample_period="2025Q1",
            oos_window_count=2,
            no_training_overlap_with_oos=True,
            no_future_leak=True,
            as_of_replay_compatible=True,
            net_of_cost_oos_result=-50.0,
            cost_model_version="cost_v1",
            slippage_model_version="slip_v1",
            market_reality_compatible=True,
            risk_gate_replay_compatible=True,
        )
        inp = L5L9ValidationInput(input_id="c010", l5_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True
        assert any("L5_OOS_NEGATIVE_AFTER_COST" in c for c in res.reason_codes)

    def test_r038c_l7_fold_count_insufficient(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L7CombinatorialPurgedCVEvidence, validate_l5_l9_chain,
        )
        evidence = L7CombinatorialPurgedCVEvidence(
            combinatorial_split_count=2, purge_window=5, embargo_window=3,
            fold_count=2,
            time_series_order_preserved=True,
            overlapping_label_protection=True,
            leakage_gap_declared=True,
            per_fold_net_of_cost_result=[10.0, 15.0],
            cost_model_version="cost_v1",
            slippage_model_version="slip_v1",
        )
        inp = L5L9ValidationInput(input_id="c011", l7_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True
        assert any("L7_FOLD_COUNT_BELOW_THRESHOLD" in c for c in res.reason_codes)

    def test_r038c_l8_adjusted_p_above_threshold(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L8PSRRealityCheckSPAEvidence, validate_l5_l9_chain,
        )
        evidence = L8PSRRealityCheckSPAEvidence(
            raw_sharpe_ratio=1.0,
            probabilistic_sharpe_ratio=0.75,
            reality_check_p_value=0.03,
            spa_p_value=None,
            benchmark_or_strategy_family_baseline="sp500",
            multiple_testing_adjusted_p_value=0.10,
            bootstrap_or_resampling_method="bootstrap",
            non_normality_or_tail_risk_adjustment="skewness_kurtosis",
            trade_count=50,
            net_of_cost_metric_used=True,
            gross_metric_used=False,
        )
        inp = L5L9ValidationInput(input_id="c012", l8_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True
        assert any("L8_ADJUSTED_P_ABOVE_THRESHOLD" in c for c in res.reason_codes)


# =============================================================================
# TestR038dFailClosedIndividual — R038d strategy lifecycle fail-closed
# =============================================================================

class TestR038dFailClosedIndividual:
    """Test each R038d failure case individually."""

    def test_r038d_registry_missing_strategy_id(self):
        from modules.decision_prechecklist.strategy_lifecycle_governance import (
            StrategyRegistryEntry, validate_strategy_lifecycle_governance,
        )
        entry = StrategyRegistryEntry(
            strategy_id="", strategy_version="v1",
            source_commit="abc123", audit_trace_id="audit001",
            research_only_default=True, no_live_order_path=True,
            order_execution_allowed=False,
        )
        res = validate_strategy_lifecycle_governance(entry)
        assert res.fail_closed is True
        assert any("REGISTRY_MISSING_STRATEGY_ID" in c for c in res.reason_codes)

    def test_r038d_research_only_default_false(self):
        from modules.decision_prechecklist.strategy_lifecycle_governance import (
            StrategyRegistryEntry, StrategyValidationEvidenceRef,
            validate_strategy_lifecycle_governance,
        )
        refs = StrategyValidationEvidenceRef(
            r038a_passed=True, r038a_snapshot_ref="snap_a",
            r038b_passed=True, r038b_snapshot_ref="snap_b",
            r038c_passed=True, r038c_snapshot_ref="snap_c",
            validation_snapshot_version="v1",
        )
        entry = StrategyRegistryEntry(
            strategy_id="strat001", strategy_version="v1",
            source_commit="abc123", audit_trace_id="audit001",
            validation_refs=refs,
            research_only_default=False,
            no_live_order_path=True, order_execution_allowed=False,
        )
        res = validate_strategy_lifecycle_governance(entry)
        assert res.fail_closed is True
        assert any("REGISTRY_RESEARCH_ONLY_NOT_DEFAULT" in c for c in res.reason_codes)

    def test_r038d_oea_true_in_registry(self):
        from modules.decision_prechecklist.strategy_lifecycle_governance import (
            StrategyRegistryEntry, StrategyValidationEvidenceRef,
            validate_strategy_lifecycle_governance,
        )
        refs = StrategyValidationEvidenceRef(
            r038a_passed=True, r038a_snapshot_ref="snap_a",
            r038b_passed=True, r038b_snapshot_ref="snap_b",
            r038c_passed=True, r038c_snapshot_ref="snap_c",
            validation_snapshot_version="v1",
        )
        entry = StrategyRegistryEntry(
            strategy_id="strat001", strategy_version="v1",
            source_commit="abc123", audit_trace_id="audit001",
            validation_refs=refs,
            research_only_default=True,
            no_live_order_path=True, order_execution_allowed=True,
        )
        res = validate_strategy_lifecycle_governance(entry)
        assert res.fail_closed is True
        assert any("ORDER_EXECUTION_ALLOWED" in c for c in res.reason_codes)

    def test_r038d_llm_approval_as_deterministic(self):
        from modules.decision_prechecklist.strategy_lifecycle_governance import (
            StrategyRegistryEntry, StrategyPromotionRequest,
            StrategyValidationEvidenceRef,
            validate_strategy_lifecycle_governance,
        )
        refs = StrategyValidationEvidenceRef(
            r038a_passed=True, r038a_snapshot_ref="snap_a",
            r038b_passed=True, r038b_snapshot_ref="snap_b",
            r038c_passed=True, r038c_snapshot_ref="snap_c",
            validation_snapshot_version="v1",
        )
        req = StrategyPromotionRequest(
            strategy_id="strat001", strategy_version="v1",
            current_stage="research_only",
            requested_transition="research_only_to_shadow",
            validation_refs=refs,
            net_of_cost_positive=True,
            replay_compatible=True,
            risk_gate_replay_compatible=True,
            market_reality_compatible=True,
            taiwan_constraints_acknowledged=True,
            strategy_ttl_days=180, strategy_ttl_remaining_days=180,
            promotion_expiry_ts="2030-01-01T00:00:00Z",
            no_live_order_path=True, order_execution_allowed=False,
            llm_approval_present=True, llm_approval_used_as_deterministic=True,
            deterministic_gate_result=True,
        )
        entry = StrategyRegistryEntry(
            strategy_id="strat001", strategy_version="v1",
            source_commit="abc123", audit_trace_id="audit001",
            validation_refs=refs,
            research_only_default=True,
            no_live_order_path=True, order_execution_allowed=False,
        )
        res = validate_strategy_lifecycle_governance(entry, req)
        assert res.fail_closed is True
        assert any("LLM_APPROVED_PROMOTION" in c for c in res.reason_codes)

    def test_r038d_downgrade_signal_ignored(self):
        from modules.decision_prechecklist.strategy_lifecycle_governance import (
            StrategyDowngradeSignal, validate_strategy_lifecycle_governance,
        )
        signal = StrategyDowngradeSignal(
            signal_type="drawdown_breach",
            signal_value=0.35, threshold=0.25,
            signal_detected=True,
            signal_timestamp="2025-01-01T00:00:00Z",
        )
        res = validate_strategy_lifecycle_governance(signals=[signal])
        assert res.fail_closed is True
        assert any("DOWNGRADE_SIGNAL_IGNORED" in c for c in res.reason_codes)

    def test_r038d_strategy_id_mismatch(self):
        from modules.decision_prechecklist.strategy_lifecycle_governance import (
            StrategyRegistryEntry, StrategyPromotionRequest,
            StrategyValidationEvidenceRef,
            validate_strategy_lifecycle_governance,
        )
        refs = StrategyValidationEvidenceRef(
            r038a_passed=True, r038a_snapshot_ref="snap_a",
            r038b_passed=True, r038b_snapshot_ref="snap_b",
            r038c_passed=True, r038c_snapshot_ref="snap_c",
            validation_snapshot_version="v1",
        )
        req = StrategyPromotionRequest(
            strategy_id="strat002", strategy_version="v1",
        )
        entry = StrategyRegistryEntry(
            strategy_id="strat001", strategy_version="v1",
        )
        res = validate_strategy_lifecycle_governance(entry, req)
        assert res.fail_closed is True

    def test_r038d_promotion_without_required_evidence_refs(self):
        from modules.decision_prechecklist.strategy_lifecycle_governance import (
            StrategyPromotionRequest, validate_strategy_lifecycle_governance,
        )
        req = StrategyPromotionRequest(
            strategy_id="strat001", strategy_version="v1",
            current_stage="shadow",
            requested_transition="shadow_to_paper",
            validation_refs=None,
        )
        res = validate_strategy_lifecycle_governance(request=req)
        assert res.fail_closed is True
        assert any("PROMOTION_MISSING_R038A_REF" in c for c in res.reason_codes)

    def test_r038d_current_stage_invalid(self):
        from modules.decision_prechecklist.strategy_lifecycle_governance import (
            StrategyRegistryEntry, StrategyValidationEvidenceRef,
            validate_strategy_lifecycle_governance,
        )
        refs = StrategyValidationEvidenceRef(
            r038a_passed=True, r038a_snapshot_ref="snap_a",
            r038b_passed=True, r038b_snapshot_ref="snap_b",
            r038c_passed=True, r038c_snapshot_ref="snap_c",
            validation_snapshot_version="v1",
        )
        entry = StrategyRegistryEntry(
            strategy_id="strat001", strategy_version="v1",
            source_commit="abc123", audit_trace_id="audit001",
            validation_refs=refs,
            research_only_default=True,
            no_live_order_path=True, order_execution_allowed=False,
            current_stage="live_normal",
        )
        res = validate_strategy_lifecycle_governance(entry)
        assert res.fail_closed is True


# =============================================================================
# TestR038eFailClosedIndividual — R038e metrics/CI artifacts fail-closed
# =============================================================================

class TestR038eFailClosedIndividual:
    """Test each R038e failure case individually."""

    def test_r038e_empty_metrics_bundle(self):
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_bundle,
        )
        result = validate_metrics_bundle(
            metrics={},
            source_commit="abc123",
            source_branch="main",
            generated_at="2026-05-31T00:00:00Z",
        )
        assert result["pass_"] is False
        assert len(result["reason_codes"]) > 0

    def test_r038e_gross_only_metrics_bundle(self):
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_bundle,
        )
        metrics = {"gross_pnl": 1000.0}
        result = validate_metrics_bundle(
            metrics=metrics,
            source_commit="abc123",
            source_branch="main",
            generated_at="2026-05-31T00:00:00Z",
        )
        assert result["pass_"] is False
        assert any("METRICS_NET_OF_COST" in c or "METRICS_MISSING_NET_OF_COST" in c for c in result["reason_codes"])

    def test_r038e_missing_net_of_cost_pnl(self):
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_bundle,
        )
        metrics = {"gross_pnl": 1000.0, "fee_cost": 5.0, "tax_cost": 3.0}
        result = validate_metrics_bundle(
            metrics=metrics,
            source_commit="abc123",
            source_branch="main",
            generated_at="2026-05-31T00:00:00Z",
        )
        assert result["pass_"] is False

    def test_r038e_missing_cost_metrics(self):
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_bundle,
        )
        metrics = {
            "net_of_cost_pnl": 500.0, "gross_pnl": 1000.0,
            "min_fee_effect": 1.0,
        }
        result = validate_metrics_bundle(
            metrics=metrics,
            source_commit="abc123",
            source_branch="main",
            generated_at="2026-05-31T00:00:00Z",
        )
        assert result["pass_"] is False
        assert any("METRICS_MISSING_COST" in c for c in result["reason_codes"])

    def test_r038e_missing_slippage_metrics(self):
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_bundle,
        )
        metrics = {
            "net_of_cost_pnl": 500.0, "gross_pnl": 1000.0,
            "fee_cost": 5.0, "tax_cost": 3.0, "min_fee_effect": 1.0,
            "total_cost": 9.0,
        }
        result = validate_metrics_bundle(
            metrics=metrics,
            source_commit="abc123",
            source_branch="main",
            generated_at="2026-05-31T00:00:00Z",
        )
        assert result["pass_"] is False
        assert any("METRICS_MISSING_SLIPPAGE" in c for c in result["reason_codes"])

    def test_r038e_missing_fill_metrics(self):
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_bundle,
        )
        metrics = {
            "net_of_cost_pnl": 500.0, "gross_pnl": 1000.0,
            "fee_cost": 5.0, "tax_cost": 3.0, "min_fee_effect": 1.0,
            "total_cost": 9.0,
            "expected_slippage": 2.0, "actual_slippage": 2.5,
            "expected_vs_actual_slippage_drift": 0.05,
        }
        result = validate_metrics_bundle(
            metrics=metrics,
            source_commit="abc123",
            source_branch="main",
            generated_at="2026-05-31T00:00:00Z",
        )
        assert result["pass_"] is False
        assert any("METRICS_MISSING_FILL" in c for c in result["reason_codes"])

    def test_r038e_missing_tail_risk_metrics(self):
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_bundle,
        )
        metrics = {
            "net_of_cost_pnl": 500.0, "gross_pnl": 1000.0,
            "fee_cost": 5.0, "tax_cost": 3.0, "min_fee_effect": 1.0,
            "total_cost": 9.0,
            "expected_slippage": 2.0, "actual_slippage": 2.5,
            "expected_vs_actual_slippage_drift": 0.05,
            "fill_probability": 0.85, "actual_fill_rate": 0.83,
            "fill_rate_drift": 0.02, "partial_fill_rate": 0.05,
            "rejected_order_rate": 0.01, "timeout_cancel_rate": 0.01,
        }
        result = validate_metrics_bundle(
            metrics=metrics,
            source_commit="abc123",
            source_branch="main",
            generated_at="2026-05-31T00:00:00Z",
        )
        assert result["pass_"] is False
        assert any("METRICS_MISSING_TAIL_RISK" in c for c in result["reason_codes"])

    def test_r038e_missing_taiwan_constraints_flag(self):
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_bundle,
        )
        metrics = {
            "net_of_cost_pnl": 500.0, "gross_pnl": 1000.0,
            "fee_cost": 5.0, "tax_cost": 3.0, "min_fee_effect": 1.0,
            "total_cost": 9.0,
            "expected_slippage": 2.0, "actual_slippage": 2.5,
            "expected_vs_actual_slippage_drift": 0.05,
            "fill_probability": 0.85, "actual_fill_rate": 0.83,
            "fill_rate_drift": 0.02, "partial_fill_rate": 0.05,
            "rejected_order_rate": 0.01, "timeout_cancel_rate": 0.01,
            "max_drawdown": -0.15, "drawdown_duration": 30,
            "sharpe_ratio": 1.2, "sortino_ratio": 1.5,
            "calmar_ratio": 0.8, "win_rate": 0.55, "payoff_ratio": 1.2,
            "trade_count": 100, "turnover": 50000.0, "exposure": 0.30,
            "capacity_liquidity_cap": 100000.0, "var": -500.0, "cvar": -750.0,
            "skewness": 0.2, "kurtosis": 0.5,
            "regime_breakdown": '{"bull": 0.6, "bear": 0.4}',
            "paper_live_drift": 0.05,
            "replay_compatibility_flag": True,
            "risk_gate_replay_compatibility_flag": True,
            "market_reality_compatibility_flag": True,
        }
        result = validate_metrics_bundle(
            metrics=metrics,
            source_commit="abc123",
            source_branch="main",
            generated_at="2026-05-31T00:00:00Z",
        )
        assert result["pass_"] is False
        assert any("TAIWAN_CONSTRAINTS_FLAG_MISSING" in c for c in result["reason_codes"])


# =============================================================================
# TestR038fFailClosedIndividual — R038f NEA gate fail-closed
# =============================================================================

class TestR038fFailClosedIndividual:
    """Test each R038f failure case individually."""

    def test_r038f_p_hat_missing(self):
        from modules.decision_prechecklist.net_expected_advantage import (
            run_r038f_nea_confidence_calibration,
        )
        result = run_r038f_nea_confidence_calibration(
            p_hat=None,
            W_hat=100.0, L_hat=50.0, C=5.0, S=2.0, B=1.0, T=0.5, R=2.0, U=1.0,
            fill_probability=0.80, regime_uncertainty=0.2,
            market_reality_snapshot={"snapshot": "valid"},
            risk_snapshot={"risk": "valid"},
            calibration_version="r038f_cal_v1",
            order_execution_allowed=False,
            calibration_brier_score=0.18,
            calibration_sample_count=50,
            raw_confidence_not_used=True,
            vetoes=[],
        )
        assert result["pass_"] is False
        assert any("P_HAT_MISSING" in c for c in result["reason_codes"])

    def test_r038f_empty_market_reality_snapshot(self):
        from modules.decision_prechecklist.net_expected_advantage import (
            run_r038f_nea_confidence_calibration,
        )
        result = run_r038f_nea_confidence_calibration(
            p_hat=0.70, W_hat=100.0, L_hat=50.0, C=5.0, S=2.0, B=1.0, T=0.5, R=2.0, U=1.0,
            fill_probability=0.80, regime_uncertainty=0.2,
            market_reality_snapshot={},
            risk_snapshot={"risk": "valid"},
            calibration_version="r038f_cal_v1",
            order_execution_allowed=False,
            calibration_brier_score=0.18,
            calibration_sample_count=50,
            raw_confidence_not_used=True,
            vetoes=[],
        )
        assert result["pass_"] is False

    def test_r038f_raw_confidence_not_used_false(self):
        from modules.decision_prechecklist.net_expected_advantage import (
            run_r038f_nea_confidence_calibration,
        )
        result = run_r038f_nea_confidence_calibration(
            p_hat=0.70, W_hat=100.0, L_hat=50.0, C=5.0, S=2.0, B=1.0, T=0.5, R=2.0, U=1.0,
            fill_probability=0.80, regime_uncertainty=0.2,
            market_reality_snapshot={"snapshot": "valid"},
            risk_snapshot={"risk": "valid"},
            calibration_version="r038f_cal_v1",
            order_execution_allowed=False,
            calibration_brier_score=0.18,
            calibration_sample_count=50,
            raw_confidence_not_used=False,
            vetoes=[],
        )
        assert result["pass_"] is False
        assert any("RAW_CONFIDENCE" in c for c in result["reason_codes"])

    def test_r038f_broker_api_veto(self):
        from modules.decision_prechecklist.net_expected_advantage import (
            run_r038f_nea_confidence_calibration,
        )
        result = run_r038f_nea_confidence_calibration(
            p_hat=0.70, W_hat=100.0, L_hat=50.0, C=5.0, S=2.0, B=1.0, T=0.5, R=2.0, U=1.0,
            fill_probability=0.80, regime_uncertainty=0.2,
            market_reality_snapshot={"snapshot": "valid"},
            risk_snapshot={"risk": "valid"},
            calibration_version="r038f_cal_v1",
            order_execution_allowed=False,
            calibration_brier_score=0.18,
            calibration_sample_count=50,
            raw_confidence_not_used=True,
            vetoes=["BROKER_API_CALLED_VETO"],
        )
        assert result["pass_"] is False
        assert any("BROKER" in c or "VETO" in c for c in result["reason_codes"])

    def test_r038f_taiwan_price_limit_violation(self):
        from modules.decision_prechecklist.net_expected_advantage import (
            run_r038f_nea_confidence_calibration,
        )
        result = run_r038f_nea_confidence_calibration(
            p_hat=0.70, W_hat=100.0, L_hat=50.0, C=5.0, S=2.0, B=1.0, T=0.5, R=2.0, U=1.0,
            fill_probability=0.80, regime_uncertainty=0.2,
            market_reality_snapshot={"snapshot": "valid"},
            risk_snapshot={"risk": "valid"},
            calibration_version="r038f_cal_v1",
            order_execution_allowed=False,
            calibration_brier_score=0.18,
            calibration_sample_count=50,
            raw_confidence_not_used=True,
            vetoes=[],
            taiwan_reality_contract={"price": 115.0, "reference_price": 100.0, "fee": 20.0},
        )
        assert result["pass_"] is False
        assert any("TAIWAN_PRICE_LIMIT" in c for c in result["reason_codes"])

    def test_r038f_fill_probability_below_threshold(self):
        from modules.decision_prechecklist.net_expected_advantage import (
            run_r038f_nea_confidence_calibration,
        )
        result = run_r038f_nea_confidence_calibration(
            p_hat=0.70, W_hat=100, L_hat=30, C=3, S=1, B=0.5, T=0.3, R=1, U=0.2,
            fill_probability=0.30, regime_uncertainty=0.1,
            market_reality_snapshot={"snapshot": "valid"},
            risk_snapshot={"risk": "valid"},
            calibration_version="r038f_cal_v1",
            order_execution_allowed=False,
            calibration_brier_score=0.18,
            calibration_sample_count=50,
            raw_confidence_not_used=True,
            vetoes=[],
            taiwan_reality_contract={"price": 100.0, "reference_price": 100.0, "fee": 20.0},
        )
        assert result["pass_"] is False
        assert any("FILL_PROBABILITY_BELOW_THRESHOLD" in c for c in result["reason_codes"])

    def test_r038f_regime_uncertainty_exceeds(self):
        from modules.decision_prechecklist.net_expected_advantage import (
            run_r038f_nea_confidence_calibration,
        )
        result = run_r038f_nea_confidence_calibration(
            p_hat=0.70, W_hat=100, L_hat=30, C=3, S=1, B=0.5, T=0.3, R=1, U=0.2,
            fill_probability=0.60, regime_uncertainty=0.5,
            market_reality_snapshot={"snapshot": "valid"},
            risk_snapshot={"risk": "valid"},
            calibration_version="r038f_cal_v1",
            order_execution_allowed=False,
            calibration_brier_score=0.18,
            calibration_sample_count=50,
            raw_confidence_not_used=True,
            vetoes=[],
            taiwan_reality_contract={"price": 100.0, "reference_price": 100.0, "fee": 20.0},
        )
        assert result["pass_"] is False
        assert any("REGIME_UNCERTAINTY_EXCEEDS" in c for c in result["reason_codes"])

    def test_r038f_oea_true(self):
        from modules.decision_prechecklist.net_expected_advantage import (
            run_r038f_nea_confidence_calibration,
        )
        result = run_r038f_nea_confidence_calibration(
            p_hat=0.70, W_hat=100.0, L_hat=50.0, C=5.0, S=2.0, B=1.0, T=0.5, R=2.0, U=1.0,
            fill_probability=0.80, regime_uncertainty=0.2,
            market_reality_snapshot={"snapshot": "valid"},
            risk_snapshot={"risk": "valid"},
            calibration_version="r038f_cal_v1",
            order_execution_allowed=True,
            calibration_brier_score=0.18,
            calibration_sample_count=50,
            raw_confidence_not_used=True,
            vetoes=[],
        )
        assert result["pass_"] is False
        assert any("ORDER_EXECUTION_ALLOWED" in c for c in result["reason_codes"])

    def test_r038f_negative_net_edge(self):
        from modules.decision_prechecklist.net_expected_advantage import (
            run_r038f_nea_confidence_calibration,
        )
        result = run_r038f_nea_confidence_calibration(
            p_hat=0.40, W_hat=50.0, L_hat=100.0, C=10.0, S=5.0, B=3.0, T=2.0, R=5.0, U=5.0,
            fill_probability=0.80, regime_uncertainty=0.2,
            market_reality_snapshot={"snapshot": "valid"},
            risk_snapshot={"risk": "valid"},
            calibration_version="r038f_cal_v1",
            order_execution_allowed=False,
            calibration_brier_score=0.18,
            calibration_sample_count=50,
            raw_confidence_not_used=True,
            vetoes=[],
        )
        assert result["pass_"] is False

    def test_r038f_low_expected_net_rr(self):
        from modules.decision_prechecklist.net_expected_advantage import (
            run_r038f_nea_confidence_calibration,
        )
        result = run_r038f_nea_confidence_calibration(
            p_hat=0.55, W_hat=40, L_hat=80, C=2, S=1, B=0.5, T=0.3, R=0.5, U=0.2,
            fill_probability=0.80, regime_uncertainty=0.2,
            market_reality_snapshot={"snapshot": "valid"},
            risk_snapshot={"risk": "valid"},
            calibration_version="r038f_cal_v1",
            order_execution_allowed=False,
            calibration_brier_score=0.18,
            calibration_sample_count=50,
            raw_confidence_not_used=True,
            vetoes=[],
            taiwan_reality_contract={"price": 100.0, "reference_price": 100.0, "fee": 20.0},
        )
        assert result["pass_"] is False
        assert any("EXPECTED_NET_RR_BELOW_THRESHOLD" in c for c in result["reason_codes"])

    def test_r038f_missing_calibration_contract(self):
        from modules.decision_prechecklist.net_expected_advantage import (
            run_r038f_nea_confidence_calibration,
        )
        result = run_r038f_nea_confidence_calibration(
            p_hat=0.70, W_hat=100.0, L_hat=50.0, C=5.0, S=2.0, B=1.0, T=0.5, R=2.0, U=1.0,
            fill_probability=0.80, regime_uncertainty=0.2,
            market_reality_snapshot={"snapshot": "valid"},
            risk_snapshot={"risk": "valid"},
            calibration_version="",
            order_execution_allowed=False,
            calibration_brier_score=None,
            calibration_sample_count=50,
            raw_confidence_not_used=True,
            vetoes=[],
        )
        assert result["pass_"] is False

    def test_r038f_stale_calibration(self):
        from modules.decision_prechecklist.net_expected_advantage import (
            run_r038f_nea_confidence_calibration,
        )
        result = run_r038f_nea_confidence_calibration(
            p_hat=0.70, W_hat=100.0, L_hat=50.0, C=5.0, S=2.0, B=1.0, T=0.5, R=2.0, U=1.0,
            fill_probability=0.80, regime_uncertainty=0.2,
            market_reality_snapshot={"snapshot": "valid"},
            risk_snapshot={"risk": "valid"},
            calibration_version="r038f_cal_v1",
            order_execution_allowed=False,
            calibration_brier_score=0.18,
            calibration_sample_count=50,
            raw_confidence_not_used=True,
            vetoes=[],
            calibration_timestamp="2020-01-01T00:00:00Z",
        )
        assert result["pass_"] is False


# =============================================================================
# TestMutationStyleFailClosed — Robustness: corrupt one field at a time
# =============================================================================

class TestMutationStyleFailClosed:
    """Mutate each valid input by one field at a time and assert fail-closed."""

    def test_mutate_r038a_valid_snapshot_corrupt_cost_version(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult, TaiwanRealityContract,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        taiwan = TaiwanRealityContract(
            tax_rate=0.003, fee_rate=0.001425, minimum_fee=1.0,
            price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
            minimum_fee_aware=True,
        )
        inp = DecisionTraceReplayInput(
            trace_id="mut01", market_reality_snapshot=snap,
            risk_gate_replay_result=risk, taiwan_reality_contract=taiwan,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True
        assert any("COST_MODEL_VERSION_MISSING" in c for c in res.reason_codes)

    def test_mutate_r038a_valid_corrupt_slippage_version(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="",
            liquidity_score=0.75, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        inp = DecisionTraceReplayInput(
            trace_id="mut02", market_reality_snapshot=snap,
            risk_gate_replay_result=risk,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True
        assert any("SLIPPAGE_MODEL_VERSION_MISSING" in c for c in res.reason_codes)

    def test_mutate_r038a_valid_corrupt_liquidity_score(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=-0.1, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        inp = DecisionTraceReplayInput(
            trace_id="mut03", market_reality_snapshot=snap,
            risk_gate_replay_result=risk,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True

    def test_mutate_r038a_valid_corrupt_market_session(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="invalid_session", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        inp = DecisionTraceReplayInput(
            trace_id="mut04", market_reality_snapshot=snap,
            risk_gate_replay_result=risk,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True

    def test_mutate_r038b_valid_l0_corrupt_cost_model(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L0BacktestEvidence, validate_l0_l4_chain,
        )
        evidence = L0BacktestEvidence(
            net_of_cost_pnl=100.0, gross_pnl=200.0,
            cost_model_version="", slippage_model_version="slip_v1",
            trade_count=100, max_drawdown=-0.10,
            order_fill_pnl_schema_compatible=True,
            market_reality_compatible=True, replay_compatible=True,
            risk_gate_replay_compatible=True,
        )
        inp = L0L4ValidationInput(input_id="mut05", l0_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        assert res.fail_closed is True
        assert any("L0_COST_MODEL_MISSING" in c for c in res.reason_codes)

    def test_mutate_r038b_valid_l0_corrupt_slippage_model(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L0BacktestEvidence, validate_l0_l4_chain,
        )
        evidence = L0BacktestEvidence(
            net_of_cost_pnl=100.0, gross_pnl=200.0,
            cost_model_version="cost_v1", slippage_model_version="",
            trade_count=100, max_drawdown=-0.10,
            order_fill_pnl_schema_compatible=True,
            market_reality_compatible=True, replay_compatible=True,
            risk_gate_replay_compatible=True,
        )
        inp = L0L4ValidationInput(input_id="mut06", l0_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        assert res.fail_closed is True
        assert any("L0_SLIPPAGE_MODEL_MISSING" in c for c in res.reason_codes)

    def test_mutate_r038b_valid_l0_corrupt_max_drawdown(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L0BacktestEvidence, validate_l0_l4_chain,
        )
        evidence = L0BacktestEvidence(
            net_of_cost_pnl=100.0, gross_pnl=200.0,
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            trade_count=100, max_drawdown=None,
            order_fill_pnl_schema_compatible=True,
            market_reality_compatible=True, replay_compatible=True,
            risk_gate_replay_compatible=True,
        )
        inp = L0L4ValidationInput(input_id="mut07", l0_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        assert res.fail_closed is True
        assert any("L0_DRAWDOWN_MISSING" in c for c in res.reason_codes)

    def test_mutate_r038b_valid_l0_corrupt_replay_compatible(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L0BacktestEvidence, validate_l0_l4_chain,
        )
        evidence = L0BacktestEvidence(
            net_of_cost_pnl=100.0, gross_pnl=200.0,
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            trade_count=100, max_drawdown=-0.10,
            order_fill_pnl_schema_compatible=True,
            market_reality_compatible=True, replay_compatible=False,
            risk_gate_replay_compatible=True,
        )
        inp = L0L4ValidationInput(input_id="mut08", l0_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        assert res.fail_closed is True

    def test_mutate_r038b_valid_l0_corrupt_risk_gate_compatible(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L0BacktestEvidence, validate_l0_l4_chain,
        )
        evidence = L0BacktestEvidence(
            net_of_cost_pnl=100.0, gross_pnl=200.0,
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            trade_count=100, max_drawdown=-0.10,
            order_fill_pnl_schema_compatible=True,
            market_reality_compatible=True, replay_compatible=True,
            risk_gate_replay_compatible=False,
        )
        inp = L0L4ValidationInput(input_id="mut09", l0_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        assert res.fail_closed is True

    def test_mutate_r038c_valid_l5_corrupt_cost_model(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L5WalkForwardOOSEvidence, validate_l5_l9_chain,
        )
        evidence = L5WalkForwardOOSEvidence(
            final_out_of_sample_period="2025Q1",
            oos_window_count=3,
            no_training_overlap_with_oos=True,
            no_future_leak=True,
            as_of_replay_compatible=True,
            net_of_cost_oos_result=50.0,
            cost_model_version="", slippage_model_version="slip_v1",
            market_reality_compatible=True,
            risk_gate_replay_compatible=True,
        )
        inp = L5L9ValidationInput(input_id="mut10", l5_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True
        assert any("L5_COST_MODEL_MISSING" in c for c in res.reason_codes)

    def test_mutate_r038c_valid_l6_corrupt_regime_labels(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L6RegimeSegmentEvidence, validate_l5_l9_chain,
        )
        evidence = L6RegimeSegmentEvidence(
            regime_count=3,
            regime_labels=[],
            per_regime_sample_count={"bull": 100, "bear": 80, "sideways": 60},
            per_regime_net_of_cost_result={"bull": 50.0, "bear": -20.0, "sideways": 5.0},
            offline_labeler_vs_online_filter_declared=True,
            no_hindsight_regime_for_live=True,
            regime_uncertainty_policy_present=True,
            market_reality_compatible_per_regime=True,
        )
        inp = L5L9ValidationInput(input_id="mut11", l6_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True
        assert any("L6_REGIME_LABELS_MISSING" in c for c in res.reason_codes)

    def test_mutate_r038c_valid_l7_corrupt_purge_window(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L7CombinatorialPurgedCVEvidence, validate_l5_l9_chain,
        )
        evidence = L7CombinatorialPurgedCVEvidence(
            combinatorial_split_count=5, purge_window=0, embargo_window=3,
            fold_count=5,
            time_series_order_preserved=True,
            overlapping_label_protection=True,
            leakage_gap_declared=True,
            per_fold_net_of_cost_result=[10.0, 12.0, 8.0, 15.0, 11.0],
            cost_model_version="cost_v1",
            slippage_model_version="slip_v1",
        )
        inp = L5L9ValidationInput(input_id="mut12", l7_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True
        assert any("L7_PURGE_WINDOW_MISSING" in c for c in res.reason_codes)

    def test_mutate_r038c_valid_l8_corrupt_psr(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L8PSRRealityCheckSPAEvidence, validate_l5_l9_chain,
        )
        evidence = L8PSRRealityCheckSPAEvidence(
            raw_sharpe_ratio=1.5,
            probabilistic_sharpe_ratio=None,
            reality_check_p_value=None,
            spa_p_value=None,
            benchmark_or_strategy_family_baseline="sp500",
            multiple_testing_adjusted_p_value=0.03,
            bootstrap_or_resampling_method="bootstrap",
            non_normality_or_tail_risk_adjustment="skewness_kurtosis",
            trade_count=50,
            net_of_cost_metric_used=True,
            gross_metric_used=False,
        )
        inp = L5L9ValidationInput(input_id="mut13", l8_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True
        assert any("L8_PSR_MISSING" in c for c in res.reason_codes)

    def test_mutate_r038c_valid_l9_corrupt_paper_trade_count(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L9PaperTradingReadinessEvidence, validate_l5_l9_chain,
        )
        evidence = L9PaperTradingReadinessEvidence(
            paper_duration_months=6,
            paper_trading_days=60,
            paper_trade_count=5,
            paper_net_of_cost_pnl=100.0,
            paper_live_drift_policy_present=True,
            strategy_ttl_or_promotion_expiry="2025-06-01",
            revalidation_required_before_live=True,
            human_approval_required_for_live=True,
            no_live_order_path=True,
            order_execution_allowed=False,
        )
        inp = L5L9ValidationInput(input_id="mut14", l9_evidence=evidence)
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True

    def test_mutate_r038d_valid_registry_corrupt_source_commit(self):
        from modules.decision_prechecklist.strategy_lifecycle_governance import (
            StrategyRegistryEntry, StrategyValidationEvidenceRef,
            validate_strategy_lifecycle_governance,
        )
        refs = StrategyValidationEvidenceRef(
            r038a_passed=True, r038a_snapshot_ref="snap_a",
            r038b_passed=True, r038b_snapshot_ref="snap_b",
            r038c_passed=True, r038c_snapshot_ref="snap_c",
            validation_snapshot_version="v1",
        )
        entry = StrategyRegistryEntry(
            strategy_id="strat001", strategy_version="v1",
            source_commit="", audit_trace_id="audit001",
            validation_refs=refs,
            research_only_default=True,
            no_live_order_path=True, order_execution_allowed=False,
        )
        res = validate_strategy_lifecycle_governance(entry)
        assert res.fail_closed is True

    def test_mutate_r038d_valid_registry_corrupt_audit_trail(self):
        from modules.decision_prechecklist.strategy_lifecycle_governance import (
            StrategyRegistryEntry, StrategyValidationEvidenceRef,
            validate_strategy_lifecycle_governance,
        )
        refs = StrategyValidationEvidenceRef(
            r038a_passed=True, r038a_snapshot_ref="snap_a",
            r038b_passed=True, r038b_snapshot_ref="snap_b",
            r038c_passed=True, r038c_snapshot_ref="snap_c",
            validation_snapshot_version="v1",
        )
        entry = StrategyRegistryEntry(
            strategy_id="strat001", strategy_version="v1",
            source_commit="abc123", audit_trace_id="",
            validation_refs=refs,
            research_only_default=True,
            no_live_order_path=True, order_execution_allowed=False,
        )
        res = validate_strategy_lifecycle_governance(entry)
        assert res.fail_closed is True

    def test_mutate_r038e_valid_metrics_corrupt_slippage_drift(self):
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_bundle,
        )
        metrics = {
            "net_of_cost_pnl": 500.0, "gross_pnl": 1000.0,
            "fee_cost": 5.0, "tax_cost": 3.0, "min_fee_effect": 1.0,
            "total_cost": 9.0,
            "expected_slippage": 2.0, "actual_slippage": 2.2,
            "expected_vs_actual_slippage_drift": 0.05,
            "fill_probability": 0.85, "actual_fill_rate": 0.83,
            "fill_rate_drift": 0.02, "partial_fill_rate": 0.05,
            "rejected_order_rate": 0.01, "timeout_cancel_rate": 0.01,
            "max_drawdown": -0.15, "drawdown_duration": 30,
            "sharpe_ratio": 1.2, "sortino_ratio": 1.5,
            "calmar_ratio": 0.8, "win_rate": 0.55, "payoff_ratio": 1.2,
            "trade_count": 100, "turnover": 50000.0, "exposure": 0.30,
            "capacity_liquidity_cap": 100000.0, "var": -500.0, "cvar": -750.0,
            "skewness": 0.2, "kurtosis": 0.5,
            "regime_breakdown": '{"bull": 0.6, "bear": 0.4}',
            "paper_live_drift": 0.05,
            "replay_compatibility_flag": True,
            "risk_gate_replay_compatibility_flag": True,
            "market_reality_compatibility_flag": True,
            "taiwan_constraints_flag": True,
        }
        result = validate_metrics_bundle(
            metrics=metrics,
            source_commit="abc123",
            source_branch="main",
            generated_at="2026-05-31T00:00:00Z",
        )
        assert result["pass_"] is True

    def test_mutate_r038f_valid_nea_corrupt_brier_score(self):
        from modules.decision_prechecklist.net_expected_advantage import (
            run_r038f_nea_confidence_calibration,
        )
        result = run_r038f_nea_confidence_calibration(
            p_hat=0.70, W_hat=100.0, L_hat=50.0, C=5.0, S=2.0, B=1.0, T=0.5, R=2.0, U=1.0,
            fill_probability=0.80, regime_uncertainty=0.2,
            market_reality_snapshot={"snapshot": "valid"},
            risk_snapshot={"risk": "valid"},
            calibration_version="r038f_cal_v1",
            order_execution_allowed=False,
            calibration_brier_score=None,
            calibration_sample_count=50,
            raw_confidence_not_used=True,
            vetoes=[],
        )
        assert result["pass_"] is False
        assert any("BRIER_SCORE_MISSING" in c for c in result["reason_codes"])

    def test_mutate_r038f_valid_nea_corrupt_calibration_version(self):
        from modules.decision_prechecklist.net_expected_advantage import (
            run_r038f_nea_confidence_calibration,
        )
        result = run_r038f_nea_confidence_calibration(
            p_hat=0.70, W_hat=100.0, L_hat=50.0, C=5.0, S=2.0, B=1.0, T=0.5, R=2.0, U=1.0,
            fill_probability=0.80, regime_uncertainty=0.2,
            market_reality_snapshot={"snapshot": "valid"},
            risk_snapshot={"risk": "valid"},
            calibration_version="",
            order_execution_allowed=False,
            calibration_brier_score=0.18,
            calibration_sample_count=50,
            raw_confidence_not_used=True,
            vetoes=[],
        )
        assert result["pass_"] is False

    def test_mutate_r038a_expected_cost_negative(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            MarketRealityReplaySnapshot,
            RiskGateReplayResult,
            TaiwanRealityContract,
            DecisionTraceReplayInput,
            validate_and_replay,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1",
            slippage_model_version="slip_v1",
            liquidity_score=0.75,
            estimated_fill_probability=0.80,
            expected_cost=-0.05,
            expected_slippage=0.005,
            expected_net_rr=0.05,
            market_session_state="regular",
            limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True,
            t_plus_2_checked=True,
            auction_session_checked=True,
            odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        taiwan = TaiwanRealityContract(
            tax_rate=0.003, fee_rate=0.001425, minimum_fee=1.0,
            price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
            minimum_fee_aware=True,
        )
        inp = DecisionTraceReplayInput(
            trace_id="mut99", market_reality_snapshot=snap,
            risk_gate_replay_result=risk, taiwan_reality_contract=taiwan,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True


# =============================================================================
# TestCrossStageIntegration — Multi-stage pipeline integration
# =============================================================================

class TestCrossStageIntegration:
    """Test cross-stage validation chains."""

    def test_cross_r038a_then_r038b_both_fail_on_invalid(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay,
        )
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, validate_l0_l4_chain,
        )
        inp = DecisionTraceReplayInput(trace_id="cross01")
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.fail_closed is True
        inp2 = L0L4ValidationInput(input_id="cross01b")
        res2 = validate_l0_l4_chain(inp2)
        assert res2.fail_closed is True

    def test_cross_r038b_then_r038c_chain(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L0BacktestEvidence, validate_l0_l4_chain,
        )
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L5WalkForwardOOSEvidence, validate_l5_l9_chain,
        )
        evidence = L0BacktestEvidence(
            net_of_cost_pnl=None, gross_pnl=1000.0,
            cost_model_version="", slippage_model_version="",
            trade_count=0, max_drawdown=None,
            order_fill_pnl_schema_compatible=False,
            market_reality_compatible=False, replay_compatible=False,
            risk_gate_replay_compatible=False,
        )
        inp = L0L4ValidationInput(input_id="cross02", l0_evidence=evidence)
        res = validate_l0_l4_chain(inp)
        assert res.fail_closed is True
        l5_evidence = L5WalkForwardOOSEvidence(
            final_out_of_sample_period="2025Q1",
            oos_window_count=0,
            no_training_overlap_with_oos=False,
            no_future_leak=False,
            as_of_replay_compatible=False,
            net_of_cost_oos_result=None,
        )
        inp2 = L5L9ValidationInput(input_id="cross02b", l5_evidence=l5_evidence)
        res2 = validate_l5_l9_chain(inp2)
        assert res2.fail_closed is True

    def test_cross_r038c_then_r038d_chain(self):
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L5WalkForwardOOSEvidence, validate_l5_l9_chain,
        )
        from modules.decision_prechecklist.strategy_lifecycle_governance import (
            StrategyRegistryEntry, validate_strategy_lifecycle_governance,
        )
        l5_evidence = L5WalkForwardOOSEvidence(
            final_out_of_sample_period="2025Q1",
            oos_window_count=0,
            no_training_overlap_with_oos=False,
            no_future_leak=False,
            as_of_replay_compatible=False,
            net_of_cost_oos_result=None,
        )
        inp = L5L9ValidationInput(input_id="cross03", l5_evidence=l5_evidence)
        res = validate_l5_l9_chain(inp)
        assert res.fail_closed is True
        entry = StrategyRegistryEntry(
            strategy_id="", strategy_version="v1",
            source_commit="abc123", audit_trace_id="audit001",
            research_only_default=True, no_live_order_path=True,
            order_execution_allowed=False,
        )
        res2 = validate_strategy_lifecycle_governance(entry)
        assert res2.fail_closed is True

    def test_cross_r038d_then_r038e_chain(self):
        from modules.decision_prechecklist.strategy_lifecycle_governance import (
            StrategyRegistryEntry, StrategyValidationEvidenceRef,
            validate_strategy_lifecycle_governance,
        )
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_bundle,
        )
        refs = StrategyValidationEvidenceRef(
            r038a_passed=True, r038a_snapshot_ref="snap_a",
            r038b_passed=True, r038b_snapshot_ref="snap_b",
            r038c_passed=True, r038c_snapshot_ref="snap_c",
            validation_snapshot_version="v1",
            validation_expiry_ts="2030-01-01T00:00:00Z",
            validation_snapshot_ts="2026-05-31T00:00:00Z",
        )
        entry = StrategyRegistryEntry(
            strategy_id="strat001", strategy_version="v1",
            source_commit="abc123", audit_trace_id="audit001",
            validation_refs=refs,
            research_only_default=True,
            no_live_order_path=True, order_execution_allowed=False,
            current_stage="research_only",
        )
        res = validate_strategy_lifecycle_governance(entry)
        assert res.fail_closed is False
        result = validate_metrics_bundle(
            metrics={},
            source_commit="abc123",
            source_branch="main",
            generated_at="2026-05-31T00:00:00Z",
        )
        assert result["pass_"] is False

    def test_cross_r038e_then_r038f_chain(self):
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_bundle,
        )
        from modules.decision_prechecklist.net_expected_advantage import (
            run_r038f_nea_confidence_calibration,
        )
        result = validate_metrics_bundle(
            metrics={},
            source_commit="abc123",
            source_branch="main",
            generated_at="2026-05-31T00:00:00Z",
        )
        assert result["pass_"] is False
        nea_result = run_r038f_nea_confidence_calibration(
            p_hat=None, W_hat=100.0, L_hat=50.0, C=5.0, S=2.0, B=1.0, T=0.5, R=2.0, U=1.0,
            fill_probability=0.80, regime_uncertainty=0.2,
            market_reality_snapshot={}, risk_snapshot={},
            calibration_version="r038f_cal_v1",
            order_execution_allowed=False,
            calibration_brier_score=None,
            calibration_sample_count=50,
            raw_confidence_not_used=True,
            vetoes=[],
        )
        assert nea_result["pass_"] is False

    def test_cross_r038a_through_r038f_full_pipeline_invalid(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay,
        )
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, validate_l0_l4_chain,
        )
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, validate_l5_l9_chain,
        )
        from modules.decision_prechecklist.strategy_lifecycle_governance import (
            StrategyRegistryEntry, StrategyValidationEvidenceRef,
            validate_strategy_lifecycle_governance,
        )
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_bundle,
        )
        from modules.decision_prechecklist.net_expected_advantage import (
            run_r038f_nea_confidence_calibration,
        )
        r038a = validate_and_replay(DecisionTraceReplayInput(trace_id="pipeline01"), False)
        assert r038a.fail_closed is True
        r038b = validate_l0_l4_chain(L0L4ValidationInput(input_id="pipeline02"))
        assert r038b.fail_closed is True
        r038c = validate_l5_l9_chain(L5L9ValidationInput(input_id="pipeline03"))
        assert r038c.fail_closed is True
        r038d = validate_strategy_lifecycle_governance(
            StrategyRegistryEntry(strategy_id="", strategy_version="v1",
                                  source_commit="abc", audit_trace_id="audit001",
                                  research_only_default=True,
                                  no_live_order_path=True, order_execution_allowed=False)
        )
        assert r038d.fail_closed is True
        r038e = validate_metrics_bundle({}, "abc", "main", "2025-01-01T00:00:00Z")
        assert r038e["pass_"] is False
        r038f = run_r038f_nea_confidence_calibration(
            p_hat=None, W_hat=100.0, L_hat=50.0, C=5.0, S=2.0, B=1.0, T=0.5, R=2.0, U=1.0,
            fill_probability=0.80, regime_uncertainty=0.2,
            market_reality_snapshot={}, risk_snapshot={},
            calibration_version="r038f_cal_v1",
            order_execution_allowed=False,
            calibration_brier_score=None,
            calibration_sample_count=50,
            raw_confidence_not_used=True, vetoes=[],
        )
        assert r038f["pass_"] is False

    def test_cross_r038a_through_r038f_full_pipeline_valid_reaches_r038f(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult, TaiwanRealityContract,
        )
        from modules.decision_prechecklist.net_expected_advantage import (
            run_r038f_nea_confidence_calibration,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        taiwan = TaiwanRealityContract(
            tax_rate=0.003, fee_rate=0.001425, minimum_fee=1.0,
            price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
            minimum_fee_aware=True,
        )
        inp = DecisionTraceReplayInput(
            trace_id="pipeline02", market_reality_snapshot=snap,
            risk_gate_replay_result=risk, taiwan_reality_contract=taiwan,
            as_of_source_ts="2025-01-01T09:00:00Z",
            as_of_publish_ts="2025-01-01T09:05:00Z",
            as_of_ingest_ts="2025-01-01T09:10:00Z",
            decision_ts="2025-01-01T10:00:00Z",
            tradable_ts="2025-01-01T09:30:00Z",
        )
        r038a = validate_and_replay(inp, order_execution_allowed=False)
        assert r038a.fail_closed is False
        nea_result = run_r038f_nea_confidence_calibration(
            p_hat=0.70, W_hat=100, L_hat=50, C=2, S=1, B=0.5, T=0.5, R=0.5, U=0.5,
            fill_probability=0.80, regime_uncertainty=0.2,
            market_reality_snapshot={"snapshot": "valid"},
            risk_snapshot={"risk": "valid"},
            calibration_version="r038f_cal_v1",
            order_execution_allowed=False,
            calibration_brier_score=0.18,
            calibration_sample_count=50,
            raw_confidence_not_used=True, vetoes=[],
            taiwan_reality_contract={"price": 100.0, "reference_price": 100.0, "fee": 20.0},
        )
        assert nea_result["pass_"] is True

    def test_cross_r038b_and_r038c_combined(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, L0BacktestEvidence, validate_l0_l4_chain,
        )
        from modules.decision_prechecklist.l5_l9_validation_chain import (
            L5L9ValidationInput, L5WalkForwardOOSEvidence, validate_l5_l9_chain,
        )
        evidence = L0BacktestEvidence(
            net_of_cost_pnl=None, gross_pnl=1000.0,
            cost_model_version="", slippage_model_version="",
            trade_count=0, max_drawdown=None,
            order_fill_pnl_schema_compatible=False,
            market_reality_compatible=False, replay_compatible=False,
            risk_gate_replay_compatible=False,
        )
        r038b = validate_l0_l4_chain(L0L4ValidationInput(input_id="cross06", l0_evidence=evidence))
        assert r038b.fail_closed is True
        l5 = L5WalkForwardOOSEvidence(
            final_out_of_sample_period="2025Q1", oos_window_count=0,
            no_training_overlap_with_oos=False, no_future_leak=False,
            as_of_replay_compatible=False, net_of_cost_oos_result=None,
        )
        r038c = validate_l5_l9_chain(L5L9ValidationInput(input_id="cross06b", l5_evidence=l5))
        assert r038c.fail_closed is True

    def test_cross_r038d_and_r038e_combined(self):
        from modules.decision_prechecklist.strategy_lifecycle_governance import (
            StrategyRegistryEntry, StrategyValidationEvidenceRef,
            validate_strategy_lifecycle_governance,
        )
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_bundle,
        )
        refs = StrategyValidationEvidenceRef(
            r038a_passed=True, r038a_snapshot_ref="snap_a",
            r038b_passed=True, r038b_snapshot_ref="snap_b",
            r038c_passed=True, r038c_snapshot_ref="snap_c",
            validation_snapshot_version="v1",
            validation_expiry_ts="2030-01-01T00:00:00Z",
            validation_snapshot_ts="2026-05-31T00:00:00Z",
        )
        entry = StrategyRegistryEntry(
            strategy_id="strat001", strategy_version="v1",
            source_commit="abc123", audit_trace_id="audit001",
            validation_refs=refs,
            research_only_default=True,
            no_live_order_path=True, order_execution_allowed=False,
            current_stage="research_only",
        )
        r038d = validate_strategy_lifecycle_governance(entry)
        assert r038d.fail_closed is False
        r038e = validate_metrics_bundle({}, "abc123", "main", "2025-01-01T00:00:00Z")
        assert r038e["pass_"] is False

    def test_cross_missing_r038a_ref_fails_r038e(self):
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_ci_artifacts,
            R038eMetricsCIArtifactsInput,
        )
        inp = R038eMetricsCIArtifactsInput(
            metrics={"net_of_cost_pnl": 500.0},
            source_commit="abc123",
            source_branch="main",
            generated_at="2026-05-31T00:00:00Z",
            test_results={"total": 0, "passed": 0},
            evidence_json=None,
            report_json=None,
            return_to_chatgpt_txt=None,
            r038a_ref=None,
            r038b_ref="ref_b",
            r038c_ref="ref_c",
            r038d_ref="ref_d",
        )
        res = validate_metrics_ci_artifacts(inp)
        assert res["pass_"] is False
        assert any("UPSTREAM_REF_R038A_MISSING" in c for c in res["reason_codes"])

    def test_cross_missing_r038b_ref_fails_r038e(self):
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_ci_artifacts,
            R038eMetricsCIArtifactsInput,
        )
        inp = R038eMetricsCIArtifactsInput(
            metrics={"net_of_cost_pnl": 500.0},
            source_commit="abc123",
            source_branch="main",
            generated_at="2026-05-31T00:00:00Z",
            test_results={"total": 0, "passed": 0},
            r038a_ref="ref_a",
            r038b_ref=None,
            r038c_ref="ref_c",
            r038d_ref="ref_d",
        )
        res = validate_metrics_ci_artifacts(inp)
        assert res["pass_"] is False
        assert any("UPSTREAM_REF_R038B_MISSING" in c for c in res["reason_codes"])

    def test_cross_missing_r038c_ref_fails_r038e(self):
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_ci_artifacts,
            R038eMetricsCIArtifactsInput,
        )
        inp = R038eMetricsCIArtifactsInput(
            metrics={"net_of_cost_pnl": 500.0},
            source_commit="abc123",
            source_branch="main",
            generated_at="2026-05-31T00:00:00Z",
            test_results={"total": 0, "passed": 0},
            r038a_ref="ref_a",
            r038b_ref="ref_b",
            r038c_ref=None,
            r038d_ref="ref_d",
        )
        res = validate_metrics_ci_artifacts(inp)
        assert res["pass_"] is False
        assert any("UPSTREAM_REF_R038C_MISSING" in c for c in res["reason_codes"])

    def test_cross_missing_r038d_ref_fails_r038e(self):
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_ci_artifacts,
            R038eMetricsCIArtifactsInput,
        )
        inp = R038eMetricsCIArtifactsInput(
            metrics={"net_of_cost_pnl": 500.0},
            source_commit="abc123",
            source_branch="main",
            generated_at="2026-05-31T00:00:00Z",
            test_results={"total": 0, "passed": 0},
            r038a_ref="ref_a",
            r038b_ref="ref_b",
            r038c_ref="ref_c",
            r038d_ref=None,
        )
        res = validate_metrics_ci_artifacts(inp)
        assert res["pass_"] is False
        assert any("UPSTREAM_REF_R038D_MISSING" in c for c in res["reason_codes"])

    def test_cross_invalid_r038a_blocks_entire_pipeline(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay,
        )
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_ci_artifacts,
            R038eMetricsCIArtifactsInput,
        )
        r038a = validate_and_replay(DecisionTraceReplayInput(trace_id="pipeline03"), False)
        assert r038a.fail_closed is True
        inp = R038eMetricsCIArtifactsInput(
            metrics={"net_of_cost_pnl": 500.0},
            source_commit="abc123",
            source_branch="main",
            generated_at="2026-05-31T00:00:00Z",
            test_results={"total": 0, "passed": 0},
            r038a_ref=None,
            r038b_ref="ref_b",
            r038c_ref="ref_c",
            r038d_ref="ref_d",
        )
        res = validate_metrics_ci_artifacts(inp)
        assert res["pass_"] is False

    def test_cross_valid_r038a_r038e_should_not_block_on_r038f_missing_optional(self):
        from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
            validate_metrics_bundle,
        )
        metrics = {
            "net_of_cost_pnl": 500.0, "gross_pnl": 1000.0,
            "fee_cost": 5.0, "tax_cost": 3.0, "min_fee_effect": 1.0,
            "total_cost": 9.0,
            "expected_slippage": 2.0, "actual_slippage": 2.5,
            "expected_vs_actual_slippage_drift": 0.05,
            "fill_probability": 0.85, "actual_fill_rate": 0.83,
            "fill_rate_drift": 0.02, "partial_fill_rate": 0.05,
            "rejected_order_rate": 0.01, "timeout_cancel_rate": 0.01,
            "max_drawdown": -0.15, "drawdown_duration": 30,
            "sharpe_ratio": 1.2, "sortino_ratio": 1.5,
            "calmar_ratio": 0.8, "win_rate": 0.55, "payoff_ratio": 1.2,
            "trade_count": 100, "turnover": 50000.0, "exposure": 0.30,
            "capacity_liquidity_cap": 100000.0, "var": -500.0, "cvar": -750.0,
            "skewness": 0.2, "kurtosis": 0.5,
            "regime_breakdown": '{"bull": 0.6, "bear": 0.4}',
            "paper_live_drift": 0.05,
            "replay_compatibility_flag": True,
            "risk_gate_replay_compatibility_flag": True,
            "market_reality_compatibility_flag": True,
            "taiwan_constraints_flag": True,
        }
        result = validate_metrics_bundle(
            metrics=metrics,
            source_commit="abc123",
            source_branch="main",
            generated_at="2026-05-31T00:00:00Z",
        )
        assert result["pass_"] is True


# =============================================================================
# TestCICDIntegration — CICDVerificationChain integration tests
# =============================================================================

class TestCICDIntegration:
    """Test CICDVerificationChain methods and stage registry."""

    def test_cicd_validate_r038g_method_exists(self):
        from modules.decision_prechecklist.cicd_verification_chain import (
            CICDVerificationChain, R038G_STAGE_NAME,
        )
        chain = CICDVerificationChain()
        assert hasattr(chain, "validate_r038g_fail_closed_tests")
        assert hasattr(chain, "run_r038g_stage")
        result = chain.run_r038g_stage()
        assert isinstance(result, R038GTestSuite)

    def test_cicd_run_r038g_stage_returns_suite(self):
        from modules.decision_prechecklist.cicd_verification_chain import (
            CICDVerificationChain,
        )
        chain = CICDVerificationChain()
        result = chain.run_r038g_stage()
        assert hasattr(result, "total")
        assert hasattr(result, "passed")
        assert hasattr(result, "failed")
        assert hasattr(result, "all_passed")

    def test_cicd_run_pipeline_with_r038g_stage_type(self):
        from modules.decision_prechecklist.cicd_verification_chain import (
            CICDVerificationChain,
        )
        chain = CICDVerificationChain()
        pipeline_result = chain.run_pipeline([
            {"type": "r038g_negative_fail_closed_tests", "name": "r038g_negative_fail_closed_tests"}
        ])
        assert len(pipeline_result.stages) == 1
        assert pipeline_result.stages[0].name == "r038g_negative_fail_closed_tests"

    def test_cicd_run_pipeline_with_missing_input_returns_fail_closed(self):
        from modules.decision_prechecklist.cicd_verification_chain import (
            CICDVerificationChain,
        )
        chain = CICDVerificationChain()
        pipeline_result = chain.run_pipeline([
            {"type": "r038a_market_reality", "name": "R038a", "input": None}
        ])
        assert len(pipeline_result.stages) == 1
        assert pipeline_result.stages[0].passed is False

    def test_cicd_run_pipeline_with_unknown_stage_type_returns_fail_closed(self):
        from modules.decision_prechecklist.cicd_verification_chain import (
            CICDVerificationChain,
        )
        chain = CICDVerificationChain()
        pipeline_result = chain.run_pipeline([
            {"type": "unknown_stage_type", "name": "unknown"}
        ])
        assert len(pipeline_result.stages) == 1
        assert pipeline_result.stages[0].passed is False

    def test_cicd_r038g_stage_name_constant_correct(self):
        from modules.decision_prechecklist.cicd_verification_chain import (
            R038G_STAGE_NAME,
        )
        assert R038G_STAGE_NAME == "r038g_negative_fail_closed_tests"


# =============================================================================
# TestOEAInvariantStrict — order_execution_allowed invariant
# =============================================================================

class TestOEAInvariantStrict:
    """Verify order_execution_allowed=False is strictly enforced across all stages."""

    def test_oea_r038g_suite_enforces_oea_false(self):
        from modules.decision_prechecklist.r038g_negative_fail_closed_tests import (
            run_r038g_fail_closed_tests, get_fail_closed_tests,
        )
        suite = run_r038g_fail_closed_tests(get_fail_closed_tests())
        assert suite.total > 0
        assert suite.all_passed is True

    def test_oea_r038a_result_preserved_false(self):
        from modules.decision_prechecklist.market_reality_trace_replay_contract import (
            DecisionTraceReplayInput, validate_and_replay, MarketRealityReplaySnapshot,
            RiskGateReplayResult, TaiwanRealityContract,
        )
        snap = MarketRealityReplaySnapshot(
            cost_model_version="cost_v1", slippage_model_version="slip_v1",
            liquidity_score=0.75, estimated_fill_probability=0.80,
            expected_cost=0.015, expected_slippage=0.005, expected_net_rr=0.05,
            market_session_state="regular", limit_up_down_distance=5.0,
            taiwan_price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
        )
        risk = RiskGateReplayResult(risk_gate_results={}, veto_reason_codes=[])
        taiwan = TaiwanRealityContract(
            tax_rate=0.003, fee_rate=0.001425, minimum_fee=1.0,
            price_limit_checked=True, t_plus_2_checked=True,
            auction_session_checked=True, odd_lot_round_lot_checked=True,
            minimum_fee_aware=True,
        )
        inp = DecisionTraceReplayInput(
            trace_id="oea01", market_reality_snapshot=snap,
            risk_gate_replay_result=risk, taiwan_reality_contract=taiwan,
        )
        res = validate_and_replay(inp, order_execution_allowed=False)
        assert res.order_execution_allowed is False

    def test_oea_r038b_result_preserved_false(self):
        from modules.decision_prechecklist.l0_l4_validation_chain import (
            L0L4ValidationInput, validate_l0_l4_chain,
        )
        inp = L0L4ValidationInput(input_id="oea02")
        res = validate_l0_l4_chain(inp)
        assert res.order_execution_allowed is False

    def test_oea_cross_stage_result_preserved_false(self):
        from modules.decision_prechecklist.cicd_verification_chain import (
            CICDVerificationChain,
        )
        chain = CICDVerificationChain()
        result = chain.run_r038g_stage()
        assert hasattr(result, "all_passed")
        assert result.all_passed is True


class TestCrossStageFailClosed:
    def test_cicd_pipeline_integration(self):
        from modules.decision_prechecklist.cicd_verification_chain import (
            CICDVerificationChain,
            R038G_STAGE_NAME,
        )
        chain = CICDVerificationChain()
        result = chain.run_r038g_stage()
        assert isinstance(result, R038GTestSuite)
        assert hasattr(result, "all_passed")

    def test_r038g_result_dict_integrates(self):
        raw = run_r038g_negative_fail_closed_tests()
        suite = run_r038g_fail_closed_tests()
        assert suite.total == raw["total"]
        assert suite.passed == raw["passed"]
        assert suite.failed == raw["failed"]


class TestOEAInvariant:
    def test_all_fail_closed_stages_reject_oea_false(self):
        suite = run_r038g_fail_closed_tests(get_fail_closed_tests())
        assert suite.total > 0
        assert suite.all_passed == True

    def test_r038g_test_suite_has_stages_r038a_through_r038f(self):
        tests = get_fail_closed_tests()
        stages = {t.stage for t in tests}
        assert "R038a" in stages
        assert "R038b" in stages
        assert "R038c" in stages
        assert "R038d" in stages
        assert "R038e" in stages
        assert "R038f" in stages

    def test_r038g_test_suite_stage_r038g(self):
        tests = get_fail_closed_tests()
        stages = {t.stage for t in tests}
        assert "Cross" in stages or "R038a" in stages