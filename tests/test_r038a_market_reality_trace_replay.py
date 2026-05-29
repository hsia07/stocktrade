from __future__ import annotations
import pytest
from modules.decision_prechecklist.market_reality_trace_replay_contract import (
    MarketRealityReplaySnapshot,
    DecisionTraceReplayInput,
    DecisionTraceReplayResult,
    RiskGateReplayResult,
    ReplayValidationStatus,
    OptionalOrderRef,
    OptionalFillRef,
    OptionalPnlRef,
    TaiwanRealityContract,
    validate_market_reality_snapshot,
    validate_and_replay,
    run_r038a_market_reality_trace_replay,
    check_limit_up_down,
    validate_taiwan_reality_contract,
    validate_fill_ref,
)
from modules.decision_prechecklist.cicd_verification_chain import (
    CICDVerificationChain,
    R038A_STAGE_NAME,
)


def make_valid_snapshot() -> MarketRealityReplaySnapshot:
    return MarketRealityReplaySnapshot(
        cost_model_version="v1",
        slippage_model_version="v1",
        liquidity_score=0.85,
        estimated_fill_probability=0.92,
        expected_cost=0.001,
        expected_slippage=0.0005,
        expected_net_rr=0.005,
        market_session_state="intraday",
        limit_up_down_distance=8.5,
        taiwan_price_limit_checked=True,
        t_plus_2_checked=True,
        auction_session_checked=True,
        odd_lot_round_lot_checked=True,
    )


def make_valid_taiwan_contract() -> TaiwanRealityContract:
    return TaiwanRealityContract(
        minimum_fee_aware=True,
    )


def make_valid_input(snapshot: MarketRealityReplaySnapshot | None = None) -> DecisionTraceReplayInput:
    if snapshot is None:
        snapshot = make_valid_snapshot()
    return DecisionTraceReplayInput(
        trace_id="test-trace-001",
        decision_ts="2026-05-29T10:00:00+08:00",
        strategy_id="strat-001",
        strategy_version="1.0.0",
        candidate_action="BUY",
        market_reality_snapshot=snapshot,
        risk_gate_replay_result=RiskGateReplayResult(),
        taiwan_reality_contract=make_valid_taiwan_contract(),
        threshold_config_version="v1",
        tradable_ts="2026-05-29T09:30:00+08:00",
        as_of_source_ts="2026-05-29T09:00:00+08:00",
        as_of_publish_ts="2026-05-29T09:15:00+08:00",
        as_of_ingest_ts="2026-05-29T09:20:00+08:00",
    )


class TestPositiveCases:
    def test_valid_market_reality_snapshot_no_veto_passes(self):
        inp = make_valid_input()
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.replay_passed is True
        assert result.fail_closed is False
        assert result.vetoed is False
        assert result.status == ReplayValidationStatus.PASS
        assert result.order_execution_allowed is False
        assert result.stage == "R038a_market_reality_trace_replay"
        assert result.market_reality_snapshot_hash != ""

    def test_cicd_verification_chain_calls_r038a_stage(self):
        chain = CICDVerificationChain()
        inp = make_valid_input()
        result_dict = chain.run_r038a_stage(inp, order_execution_allowed=False)
        assert result_dict["replay_passed"] is True
        assert result_dict["stage"] == "R038a_market_reality_trace_replay"
        assert result_dict["order_execution_allowed"] is False

    def test_cicd_chain_pipeline_with_r038a_stage(self):
        chain = CICDVerificationChain()
        inp = make_valid_input()
        stages = [
            {
                "type": "r038a_market_reality",
                "name": "R038a_market_reality_trace_replay",
                "input": inp,
                "order_execution_allowed": False,
            }
        ]
        result = chain.run_pipeline(stages)
        assert result.all_passed is True
        assert len(result.stages) == 1
        assert result.stages[0].name == "R038a_market_reality_trace_replay"

    def test_result_to_dict_contains_required_fields(self):
        inp = make_valid_input()
        result = validate_and_replay(inp, order_execution_allowed=False)
        d = result.to_dict()
        assert d["trace_id"] == "test-trace-001"
        assert d["stage"] == "R038a_market_reality_trace_replay"
        assert d["replay_passed"] is True
        assert d["order_execution_allowed"] is False
        assert "market_reality_snapshot_hash" in d
        assert "market_reality_snapshot_fields" in d


class TestNegativeFailClosed:
    def test_missing_market_reality_snapshot_fails_closed(self):
        inp = DecisionTraceReplayInput(
            trace_id="test-trace-002",
            decision_ts="2026-05-29T10:00:00+08:00",
            strategy_id="strat-001",
            market_reality_snapshot=None,
            risk_gate_replay_result=RiskGateReplayResult(),
            tradable_ts="2026-05-29T09:30:00+08:00",
        )
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.replay_passed is False
        assert result.fail_closed is True
        assert "MARKET_REALITY_SNAPSHOT_MISSING" in result.reason_codes
        assert result.status == ReplayValidationStatus.FAIL_CLOSED

    def test_missing_cost_model_version_fails_closed(self):
        snap = make_valid_snapshot()
        snap.cost_model_version = ""
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "COST_MODEL_VERSION_MISSING" in result.reason_codes

    def test_fill_probability_out_of_range_fails_closed(self):
        snap = make_valid_snapshot()
        snap.estimated_fill_probability = 1.5
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "FILL_PROBABILITY_OUT_OF_RANGE" in result.reason_codes

    def test_liquidity_score_out_of_range_fails_closed(self):
        snap = make_valid_snapshot()
        snap.liquidity_score = -0.1
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "LIQUIDITY_SCORE_OUT_OF_RANGE" in result.reason_codes

    def test_risk_gate_veto_exists_fails_closed(self):
        snap = make_valid_snapshot()
        risk = RiskGateReplayResult(
            risk_gate_results={"position_limit": "veto"},
            veto_reason_codes=["POSITION_LIMIT_EXCEEDED"],
            veto_actor="position_sizing",
            veto_stage="pre_trade",
            no_trade_reason="position limit exceeded",
        )
        inp = make_valid_input(snapshot=snap)
        inp.risk_gate_replay_result = risk
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.vetoed is True
        assert result.fail_closed is True
        assert "RISK_GATE_VETO_EXISTS" in result.reason_codes

    def test_liquidity_veto_reason_exists_fails_closed(self):
        snap = make_valid_snapshot()
        snap.liquidity_veto_reason = "insufficient_liquidity"
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "LIQUIDITY_VETO_REASON_EXISTS" in result.reason_codes

    def test_execution_abort_reason_exists_fails_closed(self):
        snap = make_valid_snapshot()
        snap.execution_abort_reason = "circuit_breaker_triggered"
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "EXECUTION_ABORT_REASON_EXISTS" in result.reason_codes

    def test_order_execution_allowed_true_blocks(self):
        inp = make_valid_input()
        result = validate_and_replay(inp, order_execution_allowed=True)
        assert result.replay_passed is False
        assert result.fail_closed is True
        assert result.status == ReplayValidationStatus.BLOCKED_ORDER_EXECUTION_ALLOWED
        assert "ORDER_EXECUTION_ALLOWED_NOT_FALSE" in result.reason_codes

    def test_near_limit_up_down_without_explicit_pass_fails_closed(self):
        snap = make_valid_snapshot()
        snap.limit_up_down_distance = 1.5
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "LIMIT_UP_DOWN_NEAR_LIMIT" in result.reason_codes

    def test_missing_tradable_contract_fails_closed(self):
        snap = make_valid_snapshot()
        inp = make_valid_input(snapshot=snap)
        inp.tradable_ts = ""
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "TRADABLE_CONTRACT_MISSING" in result.reason_codes
        assert result.status == ReplayValidationStatus.BLOCKED_MISSING_ASOF_CONTRACT


class TestNewlyRequiredFailClosed:
    def test_slippage_model_version_missing_fails_closed(self):
        snap = make_valid_snapshot()
        snap.slippage_model_version = ""
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "SLIPPAGE_MODEL_VERSION_MISSING" in result.reason_codes

    def test_fill_probability_missing_fails_closed(self):
        snap = make_valid_snapshot()
        snap.estimated_fill_probability = 0.0
        codes = validate_market_reality_snapshot(snap)
        assert "FILL_PROBABILITY_MISSING" not in codes
        assert "FILL_PROBABILITY_OUT_OF_RANGE" not in codes

    def test_liquidity_score_missing_fails_closed(self):
        snap = make_valid_snapshot()
        snap.liquidity_score = 0.0
        codes = validate_market_reality_snapshot(snap)
        assert "LIQUIDITY_SCORE_MISSING" not in codes

    def test_expected_net_rr_missing_fails_closed(self):
        snap = make_valid_snapshot()
        snap.expected_net_rr = 0.0
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "EXPECTED_NET_RR_NOT_POSITIVE" in result.reason_codes

    def test_expected_net_rr_not_positive_fails_closed(self):
        snap = make_valid_snapshot()
        snap.expected_net_rr = 0.0
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "EXPECTED_NET_RR_NOT_POSITIVE" in result.reason_codes

    def test_market_session_state_missing_fails_closed(self):
        snap = make_valid_snapshot()
        snap.market_session_state = ""
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "MARKET_SESSION_STATE_MISSING" in result.reason_codes

    def test_risk_gate_replay_missing_fails_closed(self):
        inp = make_valid_input()
        inp.risk_gate_replay_result = None
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "RISK_GATE_REPLAY_MISSING" in result.reason_codes

    def test_decision_ts_before_tradable_ts_fails_closed(self):
        inp = make_valid_input()
        inp.decision_ts = "2026-05-29T09:00:00+08:00"
        inp.tradable_ts = "2026-05-29T10:00:00+08:00"
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "DECISION_TS_BEFORE_TRADABLE_TS" in result.reason_codes
        assert result.status == ReplayValidationStatus.BLOCKED_MISSING_ASOF_CONTRACT


class TestBoundaryCases:
    def test_fill_probability_at_threshold(self):
        snap = make_valid_snapshot()
        snap.estimated_fill_probability = 0.0
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.replay_passed is True
        assert result.fail_closed is False

        snap2 = make_valid_snapshot()
        snap2.estimated_fill_probability = 1.0
        inp2 = make_valid_input(snapshot=snap2)
        result2 = validate_and_replay(inp2, order_execution_allowed=False)
        assert result2.replay_passed is True

    def test_expected_net_rr_barely_positive_with_costs(self):
        snap = make_valid_snapshot()
        snap.expected_net_rr = 0.0001
        snap.expected_cost = 0.001
        snap.expected_slippage = 0.0005
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.replay_passed is True
        assert result.fail_closed is False

    def test_taiwan_session_auction_handling(self):
        snap = make_valid_snapshot()
        snap.market_session_state = "auction_open"
        snap.auction_session_checked = True
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.replay_passed is True

        snap2 = make_valid_snapshot()
        snap2.market_session_state = "auction_close"
        snap2.auction_session_checked = True
        inp2 = make_valid_input(snapshot=snap2)
        result2 = validate_and_replay(inp2, order_execution_allowed=False)
        assert result2.replay_passed is True

        snap3 = make_valid_snapshot()
        snap3.market_session_state = "intraday"
        snap3.auction_session_checked = True
        inp3 = make_valid_input(snapshot=snap3)
        result3 = validate_and_replay(inp3, order_execution_allowed=False)
        assert result3.replay_passed is True

    def test_zero_cost_and_slippage_passes(self):
        snap = make_valid_snapshot()
        snap.expected_cost = 0.0
        snap.expected_slippage = 0.0
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.replay_passed is True


class TestTaiwanConstraints:
    def test_taiwan_price_limit_not_checked_fails_closed(self):
        snap = make_valid_snapshot()
        snap.taiwan_price_limit_checked = False
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "TAIWAN_PRICE_LIMIT_NOT_CHECKED" in result.reason_codes

    def test_t_plus_2_not_checked_fails_closed(self):
        snap = make_valid_snapshot()
        snap.t_plus_2_checked = False
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "T_PLUS_2_NOT_CHECKED" in result.reason_codes

    def test_auction_session_not_checked_fails_closed(self):
        snap = make_valid_snapshot()
        snap.auction_session_checked = False
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "AUCTION_SESSION_NOT_CHECKED" in result.reason_codes

    def test_odd_lot_round_lot_not_checked_fails_closed(self):
        snap = make_valid_snapshot()
        snap.odd_lot_round_lot_checked = False
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "ODD_LOT_ROUND_LOT_NOT_CHECKED" in result.reason_codes


class TestTaiwanRealityContractEnforcement:
    def test_taiwan_reality_contract_missing_fails_closed(self):
        inp = make_valid_input()
        inp.taiwan_reality_contract = None
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "TAIWAN_REALITY_CONTRACT_MISSING" in result.reason_codes

    def test_fee_rate_negative_fails_closed(self):
        inp = make_valid_input()
        inp.taiwan_reality_contract.fee_rate = -0.001
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "FEE_RATE_NEGATIVE" in result.reason_codes

    def test_tax_rate_negative_fails_closed(self):
        inp = make_valid_input()
        inp.taiwan_reality_contract.tax_rate = -0.001
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "TAX_RATE_NEGATIVE" in result.reason_codes

    def test_minimum_fee_negative_fails_closed(self):
        inp = make_valid_input()
        inp.taiwan_reality_contract.minimum_fee = -1.0
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "MINIMUM_FEE_NEGATIVE" in result.reason_codes

    def test_minimum_fee_aware_not_true_fails_closed(self):
        inp = make_valid_input()
        inp.taiwan_reality_contract.minimum_fee_aware = False
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "MINIMUM_FEE_AWARE_NOT_TRUE" in result.reason_codes

    def test_halt_disposition_attention_set_fails_closed(self):
        inp = make_valid_input()
        inp.taiwan_reality_contract.halt_disposition_attention = "halted"
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "HALT_DISPOSITION_ATTENTION_SET" in result.reason_codes

    def test_liquidity_insufficiency_set_fails_closed(self):
        inp = make_valid_input()
        inp.taiwan_reality_contract.liquidity_insufficiency = "low"
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "LIQUIDITY_INSUFFICIENCY_SET" in result.reason_codes


class TestFillRefEnforcement:
    def test_fill_rejected_fails_closed(self):
        inp = make_valid_input()
        inp.fill_ref = OptionalFillRef(fill_status="REJECTED", reject_reason="nok")
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "FILL_REJECTED_OR_FAILED" in result.reason_codes

    def test_fill_execution_abort_fails_closed(self):
        inp = make_valid_input()
        inp.fill_ref = OptionalFillRef(fill_status="EXECUTION_ABORT")
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "FILL_REJECTED_OR_FAILED" in result.reason_codes

    def test_fill_unfilled_fails_closed(self):
        inp = make_valid_input()
        inp.fill_ref = OptionalFillRef(fill_status="UNFILLED")
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "FILL_UNFILLED" in result.reason_codes

    def test_fill_timeout_cancel_fails_closed(self):
        inp = make_valid_input()
        inp.fill_ref = OptionalFillRef(fill_status="TIMEOUT_CANCEL")
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "FILL_TIMEOUT_CANCEL" in result.reason_codes

    def test_fill_cancel_pending_fails_closed(self):
        inp = make_valid_input()
        inp.fill_ref = OptionalFillRef(fill_status="CANCEL_PENDING")
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "FILL_TIMEOUT_CANCEL" in result.reason_codes

    def test_partial_fill_without_safe_policy_fails_closed(self):
        inp = make_valid_input()
        inp.fill_ref = OptionalFillRef(fill_status="PARTIAL_FILL", partial_fill_qty=50, fill_qty=100)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "PARTIAL_FILL_WITHOUT_SAFE_POLICY" in result.reason_codes

    def test_partial_fill_with_safe_policy_passes(self):
        inp = make_valid_input()
        inp.fill_ref = OptionalFillRef(
            fill_status="PARTIAL_FILL", partial_fill_qty=50, fill_qty=100,
            partial_fill_accepted=True,
        )
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.replay_passed is True
        assert "PARTIAL_FILL_WITHOUT_SAFE_POLICY" not in result.reason_codes

    def test_fill_ref_none_does_not_block(self):
        inp = make_valid_input()
        inp.fill_ref = None
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.replay_passed is True


class TestAsOfContractEnforcement:
    def test_as_of_source_ts_missing_fails_closed(self):
        inp = make_valid_input()
        inp.as_of_source_ts = ""
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "AS_OF_SOURCE_TS_MISSING" in result.reason_codes

    def test_as_of_publish_ts_missing_fails_closed(self):
        inp = make_valid_input()
        inp.as_of_publish_ts = ""
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "AS_OF_PUBLISH_TS_MISSING" in result.reason_codes

    def test_as_of_ingest_ts_missing_fails_closed(self):
        inp = make_valid_input()
        inp.as_of_ingest_ts = ""
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "AS_OF_INGEST_TS_MISSING" in result.reason_codes

    def test_as_of_monotonic_order_violated_source_publish_fails_closed(self):
        inp = make_valid_input()
        inp.as_of_source_ts = "2026-05-29T10:00:00+08:00"
        inp.as_of_publish_ts = "2026-05-29T09:00:00+08:00"
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "AS_OF_MONOTONIC_ORDER_VIOLATED" in result.reason_codes

    def test_as_of_monotonic_order_violated_publish_ingest_fails_closed(self):
        inp = make_valid_input()
        inp.as_of_publish_ts = "2026-05-29T10:00:00+08:00"
        inp.as_of_ingest_ts = "2026-05-29T09:00:00+08:00"
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "AS_OF_MONOTONIC_ORDER_VIOLATED" in result.reason_codes

    def test_as_of_monotonic_order_violated_ingest_tradable_fails_closed(self):
        inp = make_valid_input()
        inp.as_of_ingest_ts = "2026-05-29T10:00:00+08:00"
        inp.tradable_ts = "2026-05-29T09:00:00+08:00"
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "AS_OF_MONOTONIC_ORDER_VIOLATED" in result.reason_codes


class TestSessionCostSlippageEnforcement:
    def test_expected_cost_negative_fails_closed(self):
        snap = make_valid_snapshot()
        snap.expected_cost = -0.001
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "EXPECTED_COST_NEGATIVE" in result.reason_codes

    def test_expected_slippage_negative_fails_closed(self):
        snap = make_valid_snapshot()
        snap.expected_slippage = -0.001
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "EXPECTED_SLIPPAGE_NEGATIVE" in result.reason_codes

    def test_market_session_state_invalid_fails_closed(self):
        snap = make_valid_snapshot()
        snap.market_session_state = "unknown_session"
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.fail_closed is True
        assert "MARKET_SESSION_STATE_INVALID" in result.reason_codes

    def test_expected_cost_zero_passes(self):
        snap = make_valid_snapshot()
        snap.expected_cost = 0.0
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.replay_passed is True

    def test_expected_slippage_zero_passes(self):
        snap = make_valid_snapshot()
        snap.expected_slippage = 0.0
        inp = make_valid_input(snapshot=snap)
        result = validate_and_replay(inp, order_execution_allowed=False)
        assert result.replay_passed is True


class TestSnapshotHash:
    def test_snapshot_hash_deterministic(self):
        snap1 = make_valid_snapshot()
        snap2 = make_valid_snapshot()
        assert snap1.compute_deterministic_hash() == snap2.compute_deterministic_hash()

    def test_snapshot_hash_changes_with_fields(self):
        snap1 = make_valid_snapshot()
        snap2 = make_valid_snapshot()
        snap2.liquidity_score = 0.5
        assert snap1.compute_deterministic_hash() != snap2.compute_deterministic_hash()


class TestOrderRefAndResult:
    def test_fill_ref_rejected_status(self):
        fill = OptionalFillRef(
            fill_id="f-001",
            fill_qty=100,
            fill_price=150.0,
            fill_status="REJECTED",
            reject_reason="insufficient_liquidity",
        )
        assert fill.is_rejected is True
        assert fill.is_partial is False

    def test_fill_ref_partial_status(self):
        fill = OptionalFillRef(
            fill_id="f-002",
            fill_qty=100,
            fill_price=150.0,
            fill_status="PARTIAL_FILL",
            partial_fill_qty=50,
        )
        assert fill.is_rejected is False
        assert fill.is_partial is True

    def test_validate_and_replay_result_to_dict(self):
        inp = make_valid_input()
        result = validate_and_replay(inp, order_execution_allowed=False)
        d = result.to_dict()
        assert d["trace_id"] == "test-trace-001"
        assert d["stage"] == "R038a_market_reality_trace_replay"
        assert d["replay_passed"] is True
        assert d["order_execution_allowed"] is False
        assert "market_reality_snapshot_hash" in d
        assert "market_reality_snapshot_fields" in d


class TestCheckLimitUpDown:
    def test_check_limit_up_down_near_limit(self):
        snap = make_valid_snapshot()
        snap.limit_up_down_distance = 1.0
        code = check_limit_up_down(snap)
        assert code == "LIMIT_UP_DOWN_NEAR_LIMIT"

    def test_check_limit_up_down_safe(self):
        snap = make_valid_snapshot()
        snap.limit_up_down_distance = 8.5
        code = check_limit_up_down(snap)
        assert code == ""


class TestValidateSnapshot:
    def test_validate_snapshot_returns_codes(self):
        codes = validate_market_reality_snapshot(None)
        assert "MARKET_REALITY_SNAPSHOT_MISSING" in codes

    def test_validate_snapshot_all_good_returns_empty(self):
        snap = make_valid_snapshot()
        codes = validate_market_reality_snapshot(snap)
        assert codes == []


class TestValidateTaiwanRealityContract:
    def test_validate_taiwan_contract_missing(self):
        codes = validate_taiwan_reality_contract(None)
        assert "TAIWAN_REALITY_CONTRACT_MISSING" in codes

    def test_validate_taiwan_contract_valid_returns_empty(self):
        contract = make_valid_taiwan_contract()
        codes = validate_taiwan_reality_contract(contract)
        assert codes == []


class TestValidateFillRefDirect:
    def test_validate_fill_ref_none_returns_empty(self):
        codes = validate_fill_ref(None)
        assert codes == []

    def test_validate_fill_ref_valid_returns_empty(self):
        fill = OptionalFillRef(fill_status="FILLED")
        codes = validate_fill_ref(fill)
        assert codes == []
