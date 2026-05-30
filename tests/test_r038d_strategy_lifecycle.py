from __future__ import annotations
import uuid
from datetime import datetime, timezone, timedelta
from modules.decision_prechecklist.strategy_lifecycle_governance import (
    StrategyLifecycleStatus,
    StrategyLifecycleStage,
    StrategyRegistryEntry,
    StrategyValidationEvidenceRef,
    StrategyPromotionRequest,
    StrategyPromotionDecision,
    StrategyDowngradeSignal,
    StrategyLifecyclePolicy,
    StrategyLifecycleValidationResult,
    PromotionTransition,
    DowngradeAction,
    DowngradeSignalType,
    STAGE_R038D,
    FAIL_CLOSED_REASON_CODES_R038D,
    validate_strategy_registry_entry,
    validate_new_strategy_defaults,
    validate_promotion_readiness,
    validate_live_promotion_boundary,
    validate_downgrade_quarantine,
    validate_strategy_ttl_freshness,
    validate_strategy_lifecycle_governance,
    run_r038d_strategy_lifecycle,
    DEFAULT_TTL_DAYS,
    DEFAULT_VALIDATION_FRESHNESS_DAYS,
    DEFAULT_PROMOTION_EXPIRY_DAYS,
    DEFAULT_SLIPPAGE_DRIFT_THRESHOLD,
    DEFAULT_FILL_RATE_DRIFT_THRESHOLD,
    DEFAULT_DRAWDOWN_BREACH_THRESHOLD,
    DEFAULT_NET_OF_COST_DECAY_THRESHOLD,
    DEFAULT_VIRTUAL_CAPITAL_BUDGET,
    DEFAULT_REAL_CAPITAL_LOCKED,
)
from modules.decision_prechecklist.cicd_verification_chain import (
    CICDVerificationChain,
    CICDStageResult,
    R038D_STAGE_NAME,
)


def _make_valid_refs() -> StrategyValidationEvidenceRef:
    now = datetime.now(timezone.utc)
    return StrategyValidationEvidenceRef(
        r038a_passed=True,
        r038a_snapshot_ref="r038a_snap_001",
        r038b_passed=True,
        r038b_snapshot_ref="r038b_snap_001",
        r038c_passed=True,
        r038c_snapshot_ref="r038c_snap_001",
        validation_snapshot_ts=now.isoformat(),
        validation_expiry_ts=(now + timedelta(days=90)).isoformat(),
        validation_snapshot_version="v1.0",
    )


def _make_valid_entry(**kwargs) -> StrategyRegistryEntry:
    defaults = dict(
        strategy_id="strat_test_001",
        strategy_version="1.0.0",
        strategy_family="momentum",
        created_at=datetime.now(timezone.utc).isoformat(),
        registered_at=datetime.now(timezone.utc).isoformat(),
        current_status=StrategyLifecycleStatus.REGISTERED.value,
        current_stage=StrategyLifecycleStage.RESEARCH_ONLY.value,
        source_round="R038",
        source_candidate="candidate/r038d-strategy-lifecycle",
        source_commit="a285f33edf043d2224c6d7a18fbb9839dfad0549",
        validation_refs=_make_valid_refs(),
        latest_validation_level_passed="L5-L9",
        research_only_default=True,
        no_live_order_path=True,
        order_execution_allowed=False,
        owner="test_owner",
        proposer="test_proposer",
        audit_trace_id=f"audit_{uuid.uuid4().hex[:8]}",
        real_capital=0.0,
        live_enabled=False,
        broker_access=False,
    )
    defaults.update(kwargs)
    return StrategyRegistryEntry(**defaults)


def _make_valid_promotion_request(
    transition: str = PromotionTransition.RESEARCH_TO_SHADOW.value,
    **kwargs,
) -> StrategyPromotionRequest:
    now = datetime.now(timezone.utc)
    defaults = dict(
        strategy_id="strat_test_001",
        strategy_version="1.0.0",
        current_stage=StrategyLifecycleStage.RESEARCH_ONLY.value,
        requested_transition=transition,
        validation_refs=_make_valid_refs(),
        net_of_cost_positive=True,
        replay_compatible=True,
        risk_gate_replay_compatible=True,
        market_reality_compatible=True,
        taiwan_constraints_acknowledged=True,
        evidence_source="python_backtest",
        strategy_ttl_days=DEFAULT_TTL_DAYS,
        strategy_ttl_remaining_days=DEFAULT_TTL_DAYS,
        promotion_expiry_ts=(now + timedelta(days=DEFAULT_PROMOTION_EXPIRY_DAYS)).isoformat(),
        no_live_order_path=True,
        order_execution_allowed=False,
        human_approval_required=True,
        human_approval_received=False,
        deterministic_gate_result=True,
        llm_approval_present=False,
        llm_approval_used_as_deterministic=False,
        audit_trace_id=f"audit_{uuid.uuid4().hex[:8]}",
        timestamp=now.isoformat(),
    )
    defaults.update(kwargs)
    return StrategyPromotionRequest(**defaults)


def _make_policy(**kwargs) -> StrategyLifecyclePolicy:
    defaults = dict(
        strategy_id="strat_test_001",
        strategy_ttl_days=DEFAULT_TTL_DAYS,
        validation_freshness_days=DEFAULT_VALIDATION_FRESHNESS_DAYS,
        promotion_expiry_days=DEFAULT_PROMOTION_EXPIRY_DAYS,
        slippage_drift_threshold=DEFAULT_SLIPPAGE_DRIFT_THRESHOLD,
        fill_rate_drift_threshold=DEFAULT_FILL_RATE_DRIFT_THRESHOLD,
        drawdown_breach_threshold=DEFAULT_DRAWDOWN_BREACH_THRESHOLD,
        net_of_cost_decay_threshold=DEFAULT_NET_OF_COST_DECAY_THRESHOLD,
        revalidation_required_before_live=True,
        human_approval_required_for_live=True,
        human_approval_required_for_capital_increase=True,
        human_approval_required_for_live_logic_change=True,
        llm_cannot_approve_promotion=True,
        llm_cannot_set_qty=True,
        risk_gate_can_veto_allocation=True,
        qty_controlled_by_deterministic_engine=True,
        research_only_default_for_new=True,
        no_live_order_path=True,
        order_execution_allowed_default=False,
        market_reality_required=True,
        replay_required=True,
        risk_gate_replay_required=True,
        taiwan_market_constraints_required=True,
        tradingview_only_rejected=True,
        net_of_cost_required=True,
    )
    defaults.update(kwargs)
    return StrategyLifecyclePolicy(**defaults)


# ---- Positive Tests ----

class TestPositiveRegistry:
    def test_new_strategy_defaults_to_research_only(self):
        entry = _make_valid_entry()
        codes = validate_new_strategy_defaults(entry)
        assert len(codes) == 0
        assert entry.current_stage == StrategyLifecycleStage.RESEARCH_ONLY.value

    def test_valid_registry_entry_passes(self):
        entry = _make_valid_entry()
        codes = validate_strategy_registry_entry(entry)
        assert len(codes) == 0

    def test_registry_entry_with_complete_refs(self):
        entry = _make_valid_entry()
        assert entry.validation_refs.is_complete()
        assert entry.validation_refs.all_passed()
        codes = validate_strategy_registry_entry(entry)
        assert len(codes) == 0

    def test_complete_r038_validation_refs_can_recommend_shadow(self):
        request = _make_valid_promotion_request(
            transition=PromotionTransition.RESEARCH_TO_SHADOW.value,
        )
        codes = validate_promotion_readiness(request)
        assert len(codes) == 0

    def test_complete_shadow_readiness_can_recommend_paper(self):
        request = _make_valid_promotion_request(
            transition=PromotionTransition.SHADOW_TO_PAPER.value,
            current_stage=StrategyLifecycleStage.SHADOW.value,
        )
        codes = validate_promotion_readiness(request)
        assert len(codes) == 0

    def test_strategy_lifecycle_governance_passes_with_valid_data(self):
        result = validate_strategy_lifecycle_governance(
            entry=_make_valid_entry(),
            request=_make_valid_promotion_request(),
            policy=_make_policy(),
        )
        assert result.validation_passed
        assert result.registry_entry_valid
        assert result.validation_refs_present

    def test_run_r038d_strategy_lifecycle_returns_dict(self):
        d = run_r038d_strategy_lifecycle(
            entry=_make_valid_entry(),
            request=_make_valid_promotion_request(),
            policy=_make_policy(),
        )
        assert isinstance(d, dict)
        assert d["stage"] == STAGE_R038D

    def test_strategy_lifecycle_validation_result_to_dict(self):
        result = validate_strategy_lifecycle_governance(_make_valid_entry())
        d = result.to_dict()
        assert d["stage"] == STAGE_R038D
        assert "reason_codes" in d
        assert "strategy_id" in d

    def test_compute_result_hash_is_deterministic(self):
        r1 = validate_strategy_lifecycle_governance(_make_valid_entry())
        r2 = validate_strategy_lifecycle_governance(_make_valid_entry())
        assert r1.compute_result_hash() == r2.compute_result_hash()

    def test_downgrade_signal_clean_returns_no_codes(self):
        signals = [StrategyDowngradeSignal(
            signal_type=DowngradeSignalType.DRAWDOWN_BREACH.value,
            signal_value=0.05,
            threshold=DEFAULT_DRAWDOWN_BREACH_THRESHOLD,
            signal_detected=False,
        )]
        codes = validate_downgrade_quarantine(signals)
        assert len(codes) == 0

    def test_human_approval_received_for_live_passes(self):
        request = _make_valid_promotion_request(
            transition=PromotionTransition.PAPER_TO_LIVE_SMALL.value,
            current_stage=StrategyLifecycleStage.PAPER.value,
            human_approval_required=True,
            human_approval_received=True,
        )
        codes = validate_live_promotion_boundary(request)
        assert len(codes) == 0

    def test_ttl_freshness_valid_passes(self):
        refs = _make_valid_refs()
        codes = validate_strategy_ttl_freshness(refs, _make_policy())
        assert len(codes) == 0

    def test_policy_defaults_are_research_only(self):
        policy = _make_policy()
        assert policy.research_only_default_for_new
        assert not policy.order_execution_allowed_default
        assert policy.no_live_order_path
        assert policy.llm_cannot_approve_promotion
        assert policy.llm_cannot_set_qty
        assert policy.risk_gate_can_veto_allocation

    def test_cicd_chain_has_r038d_stage(self):
        chain = CICDVerificationChain()
        result = chain.run_r038d_stage(entry=_make_valid_entry())
        assert isinstance(result, dict)
        assert "stage" in result

    def test_cicd_pipeline_r038d_stage_type(self):
        chain = CICDVerificationChain()
        result = chain.run_pipeline([{
            "type": "r038d_strategy_lifecycle",
            "name": R038D_STAGE_NAME,
            "entry": _make_valid_entry(),
            "request": _make_valid_promotion_request(),
        }])
        assert result.all_passed
        assert len(result.stages) == 1
        assert result.stages[0].name == R038D_STAGE_NAME
        assert result.stages[0].passed


class TestPositivePromotionBoundary:
    def test_research_to_shadow_no_human_approval_needed(self):
        request = _make_valid_promotion_request(
            transition=PromotionTransition.RESEARCH_TO_SHADOW.value,
        )
        codes = validate_live_promotion_boundary(request)
        assert len(codes) == 0

    def test_shadow_to_paper_no_human_approval_needed(self):
        request = _make_valid_promotion_request(
            transition=PromotionTransition.SHADOW_TO_PAPER.value,
            current_stage=StrategyLifecycleStage.SHADOW.value,
        )
        codes = validate_live_promotion_boundary(request)
        assert len(codes) == 0

    def test_downgrade_action_quarantine(self):
        signals = [
            StrategyDowngradeSignal(
                signal_type=DowngradeSignalType.DRAWDOWN_BREACH.value,
                signal_value=0.30,
                threshold=DEFAULT_DRAWDOWN_BREACH_THRESHOLD,
                signal_detected=True,
            ),
        ]
        result = validate_strategy_lifecycle_governance(
            entry=_make_valid_entry(),
            signals=signals,
            policy=_make_policy(),
        )
        assert not result.validation_passed
        assert any("DOWNGRADE_SIGNAL_IGNORED" in c for c in result.reason_codes)

    def test_expired_strategy_blocks_promotion(self):
        now = datetime.now(timezone.utc)
        refs = StrategyValidationEvidenceRef(
            r038a_passed=True,
            r038a_snapshot_ref="r038a_snap",
            r038b_passed=True,
            r038b_snapshot_ref="r038b_snap",
            r038c_passed=True,
            r038c_snapshot_ref="r038c_snap",
            validation_snapshot_ts=(now - timedelta(days=200)).isoformat(),
            validation_expiry_ts=(now - timedelta(days=10)).isoformat(),
            validation_snapshot_version="v1.0",
        )
        entry = _make_valid_entry(validation_refs=refs)
        result = validate_strategy_lifecycle_governance(
            entry=entry,
            policy=_make_policy(validation_freshness_days=90),
        )
        assert not result.validation_passed
        assert any("STRATEGY_EXPIRED_VALIDATION" in c for c in result.reason_codes)

    def test_human_approval_required_for_live_paper_to_live_small(self):
        request = _make_valid_promotion_request(
            transition=PromotionTransition.PAPER_TO_LIVE_SMALL.value,
            current_stage=StrategyLifecycleStage.PAPER.value,
            human_approval_required=True,
            human_approval_received=True,
        )
        codes = validate_live_promotion_boundary(request)
        assert len(codes) == 0

    def test_human_approval_required_for_live_small_to_live_normal(self):
        request = _make_valid_promotion_request(
            transition=PromotionTransition.LIVE_SMALL_TO_LIVE_NORMAL.value,
            current_stage=StrategyLifecycleStage.LIVE_SMALL.value,
            human_approval_required=True,
            human_approval_received=True,
        )
        codes = validate_live_promotion_boundary(request)
        assert len(codes) == 0

    def test_cicd_chain_can_run_r038d_pipeline(self):
        chain = CICDVerificationChain()
        result = chain.run_pipeline([
            {"type": "r038d_strategy_lifecycle", "name": "test_r038d",
             "entry": _make_valid_entry()},
            {"type": "r038d_strategy_lifecycle", "name": "test_r038d_fail",
             "entry": None},
        ])
        assert len(result.stages) == 2
        assert result.stages[0].passed
        assert not result.stages[1].passed


# ---- Negative / Fail-Closed Tests ----

class TestNegativeRegistry:
    def test_missing_strategy_id_fails(self):
        entry = _make_valid_entry(strategy_id="")
        codes = validate_strategy_registry_entry(entry)
        assert "REGISTRY_MISSING_STRATEGY_ID" in codes

    def test_missing_strategy_version_fails(self):
        entry = _make_valid_entry(strategy_version="")
        codes = validate_strategy_registry_entry(entry)
        assert "REGISTRY_MISSING_STRATEGY_VERSION" in codes

    def test_missing_validation_refs_fails(self):
        entry = _make_valid_entry(validation_refs=None)
        codes = validate_strategy_registry_entry(entry)
        assert "REGISTRY_MISSING_VALIDATION_REFS" in codes

    def test_missing_source_commit_fails(self):
        entry = _make_valid_entry(source_commit="")
        codes = validate_strategy_registry_entry(entry)
        assert "REGISTRY_MISSING_SOURCE_COMMIT" in codes

    def test_missing_audit_trace_id_fails(self):
        entry = _make_valid_entry(audit_trace_id="")
        codes = validate_strategy_registry_entry(entry)
        assert "REGISTRY_MISSING_AUDIT_TRAIL_ID" in codes

    def test_new_strategy_starts_paper_fails(self):
        entry = _make_valid_entry(
            current_stage=StrategyLifecycleStage.PAPER.value,
        )
        codes = validate_new_strategy_defaults(entry)
        assert "NEW_STRATEGY_NOT_RESEARCH_ONLY" in codes

    def test_new_strategy_has_real_capital_fails(self):
        entry = _make_valid_entry(real_capital=10000.0)
        codes = validate_new_strategy_defaults(entry)
        assert "NEW_STRATEGY_HAS_REAL_CAPITAL" in codes

    def test_new_strategy_live_enabled_fails(self):
        entry = _make_valid_entry(live_enabled=True)
        codes = validate_new_strategy_defaults(entry)
        assert "NEW_STRATEGY_SELF_ENABLES_LIVE" in codes

    def test_broker_access_on_new_strategy_fails(self):
        entry = _make_valid_entry(broker_access=True)
        codes = validate_new_strategy_defaults(entry)
        assert "NEW_STRATEGY_SELF_ENABLES_LIVE" in codes

    def test_order_execution_allowed_true_fails(self):
        entry = _make_valid_entry(order_execution_allowed=True)
        codes = validate_strategy_registry_entry(entry)
        assert "REGISTRY_ORDER_EXECUTION_ALLOWED_TRUE" in codes

    def test_no_live_order_path_false_fails(self):
        entry = _make_valid_entry(no_live_order_path=False)
        codes = validate_strategy_registry_entry(entry)
        assert "REGISTRY_NO_LIVE_ORDER_PATH_FALSE" in codes

    def test_status_implies_live_fails(self):
        entry = _make_valid_entry(current_status=StrategyLifecycleStage.LIVE_SMALL.value)
        codes = validate_strategy_registry_entry(entry)
        assert "REGISTRY_STATUS_IMPLIES_LIVE" in codes

    def test_research_only_not_default_fails(self):
        entry = _make_valid_entry(research_only_default=False)
        codes = validate_strategy_registry_entry(entry)
        assert "REGISTRY_RESEARCH_ONLY_NOT_DEFAULT" in codes

    def test_registry_entry_none_fails(self):
        codes = validate_strategy_registry_entry(None)
        assert len(codes) >= 4


class TestNegativePromotion:
    def test_missing_r038a_ref_fails(self):
        refs = _make_valid_refs()
        refs.r038a_snapshot_ref = ""
        request = _make_valid_promotion_request(validation_refs=refs)
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_MISSING_R038A_REF" in codes

    def test_missing_r038b_ref_fails(self):
        refs = _make_valid_refs()
        refs.r038b_snapshot_ref = ""
        request = _make_valid_promotion_request(validation_refs=refs)
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_MISSING_R038B_REF" in codes

    def test_missing_r038c_ref_fails(self):
        refs = _make_valid_refs()
        refs.r038c_snapshot_ref = ""
        request = _make_valid_promotion_request(validation_refs=refs)
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_MISSING_R038C_REF" in codes

    def test_validation_stale_fails(self):
        now = datetime.now(timezone.utc)
        refs = StrategyValidationEvidenceRef(
            r038a_passed=True, r038a_snapshot_ref="a",
            r038b_passed=True, r038b_snapshot_ref="b",
            r038c_passed=True, r038c_snapshot_ref="c",
            validation_snapshot_ts=(now - timedelta(days=200)).isoformat(),
            validation_expiry_ts=(now - timedelta(days=10)).isoformat(),
            validation_snapshot_version="v1.0",
        )
        request = _make_valid_promotion_request(validation_refs=refs)
        codes = validate_promotion_readiness(request)
        assert any(c for c in codes if "STALE" in c or "EXPIRED" in c or "VALIDATION" in c)

    def test_ttl_missing_fails(self):
        request = _make_valid_promotion_request(strategy_ttl_days=0)
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_TTL_MISSING" in codes

    def test_ttl_expired_fails(self):
        request = _make_valid_promotion_request(strategy_ttl_remaining_days=0)
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_TTL_EXPIRED" in codes

    def test_promotion_expiry_missing_fails(self):
        request = _make_valid_promotion_request(promotion_expiry_ts="")
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_EXPIRY_MISSING" in codes

    def test_promotion_expiry_expired_fails(self):
        past = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        request = _make_valid_promotion_request(promotion_expiry_ts=past)
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_EXPIRY_EXPIRED" in codes

    def test_net_of_cost_not_positive_fails(self):
        request = _make_valid_promotion_request(net_of_cost_positive=False)
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_NET_OF_COST_NOT_POSITIVE" in codes

    def test_replay_not_compatible_fails(self):
        request = _make_valid_promotion_request(replay_compatible=False)
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_REPLAY_NOT_COMPATIBLE" in codes

    def test_risk_gate_replay_not_compatible_fails(self):
        request = _make_valid_promotion_request(risk_gate_replay_compatible=False)
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_RISK_GATE_REPLAY_NOT_COMPATIBLE" in codes

    def test_market_reality_not_compatible_fails(self):
        request = _make_valid_promotion_request(market_reality_compatible=False)
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_MARKET_REALITY_NOT_COMPATIBLE" in codes

    def test_taiwan_constraints_missing_fails(self):
        request = _make_valid_promotion_request(taiwan_constraints_acknowledged=False)
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_TAIWAN_CONSTRAINTS_MISSING" in codes

    def test_tradingview_only_evidence_fails(self):
        request = _make_valid_promotion_request(evidence_source="tradingview")
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_TRADINGVIEW_ONLY" in codes

    def test_broker_live_path_present_fails(self):
        request = _make_valid_promotion_request(no_live_order_path=False)
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_BROKER_LIVE_PATH_PRESENT" in codes

    def test_order_execution_allowed_true_fails_promotion(self):
        request = _make_valid_promotion_request(order_execution_allowed=True)
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_ORDER_EXECUTION_ALLOWED_TRUE" in codes

    def test_validation_not_all_passed_fails(self):
        refs = _make_valid_refs()
        refs.r038a_passed = False
        request = _make_valid_promotion_request(validation_refs=refs)
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_VALIDATION_NOT_ALL_PASSED" in codes


class TestNegativeLiveBoundary:
    def test_paper_to_live_auto_approval_fails(self):
        request = _make_valid_promotion_request(
            transition=PromotionTransition.PAPER_TO_LIVE_SMALL.value,
            current_stage=StrategyLifecycleStage.PAPER.value,
            human_approval_required=False,
            human_approval_received=False,
        )
        codes = validate_live_promotion_boundary(request)
        assert "PROMOTION_AUTO_LIVE_APPROVAL" in codes

    def test_live_small_to_live_normal_auto_approval_fails(self):
        request = _make_valid_promotion_request(
            transition=PromotionTransition.LIVE_SMALL_TO_LIVE_NORMAL.value,
            current_stage=StrategyLifecycleStage.LIVE_SMALL.value,
            human_approval_required=False,
        )
        codes = validate_live_promotion_boundary(request)
        assert "PROMOTION_AUTO_LIVE_APPROVAL" in codes

    def test_capital_increase_not_approved_fails(self):
        request = _make_valid_promotion_request(
            transition=PromotionTransition.CAPITAL_INCREASE.value,
            capital_increase_amount=50000.0,
            capital_increase_human_approved=False,
        )
        codes = validate_live_promotion_boundary(request)
        assert "PROMOTION_CAPITAL_INCREASE_MISSING_HUMAN_APPROVAL" in codes

    def test_live_core_logic_change_not_approved_fails(self):
        request = _make_valid_promotion_request(
            transition=PromotionTransition.PAPER_TO_LIVE_SMALL.value,
            current_stage=StrategyLifecycleStage.PAPER.value,
            live_core_logic_change=True,
            live_core_logic_change_human_approved=False,
            human_approval_required=True,
            human_approval_received=True,
        )
        codes = validate_live_promotion_boundary(request)
        assert "PROMOTION_LIVE_CORE_LOGIC_CHANGE_MISSING_HUMAN_APPROVAL" in codes

    def test_paper_to_live_missing_human_approval_fails(self):
        request = _make_valid_promotion_request(
            transition=PromotionTransition.PAPER_TO_LIVE_SMALL.value,
            current_stage=StrategyLifecycleStage.PAPER.value,
            human_approval_required=True,
            human_approval_received=False,
        )
        codes = validate_live_promotion_boundary(request)
        assert "PROMOTION_TO_LIVE_MISSING_HUMAN_APPROVAL" in codes


class TestNegativeLLM:
    def test_llm_approval_treated_as_deterministic_pass_fails(self):
        request = _make_valid_promotion_request(
            llm_approval_present=True,
            llm_approval_used_as_deterministic=True,
        )
        codes = validate_promotion_readiness(request)
        assert "LLM_APPROVED_PROMOTION" in codes

    def test_llm_score_moves_stage_without_deterministic_gate_fails(self):
        request = _make_valid_promotion_request(
            llm_approval_present=True,
            llm_approval_used_as_deterministic=False,
            deterministic_gate_result=False,
        )
        codes = validate_promotion_readiness(request)
        assert "LLM_MISSING_LOCAL_DETERMINISTIC_GATE" in codes

    def test_llm_cannot_set_qty_in_policy(self):
        policy = _make_policy(llm_cannot_set_qty=False)
        refs = _make_valid_refs()
        codes = validate_strategy_ttl_freshness(refs, policy)
        assert "ALLOCATION_LLM_CONTROLS_QTY" in codes

    def test_llm_cannot_approve_promotion_in_policy(self):
        policy = _make_policy(llm_cannot_approve_promotion=False)
        refs = _make_valid_refs()
        codes = validate_strategy_ttl_freshness(refs, policy)
        assert "LLM_APPROVED_PROMOTION" in codes


class TestNegativeDowngrade:
    def test_downgrade_signal_ignored_fails(self):
        signals = [StrategyDowngradeSignal(
            signal_type=DowngradeSignalType.DRAWDOWN_BREACH.value,
            signal_value=0.30,
            threshold=DEFAULT_DRAWDOWN_BREACH_THRESHOLD,
            signal_detected=True,
        )]
        codes = validate_downgrade_quarantine(signals)
        assert "DOWNGRADE_SIGNAL_IGNORED" in codes

    def test_quarantined_strategy_promotable_fails(self):
        signals = [StrategyDowngradeSignal(
            signal_type=DowngradeSignalType.MANUAL_BLOCK.value,
            signal_value=1.0,
            threshold=0.0,
            signal_detected=True,
        )]
        codes = validate_downgrade_quarantine(signals)
        assert "DOWNGRADE_SIGNAL_IGNORED" in codes
        assert "DOWNGRADE_GOVERNANCE_BLOCK_IGNORED" in codes

    def test_market_reality_failure_still_promotable_fails(self):
        signals = [StrategyDowngradeSignal(
            signal_type=DowngradeSignalType.MARKET_REALITY_FAILURE.value,
            signal_value=1.0,
            threshold=0.0,
            signal_detected=True,
        )]
        codes = validate_downgrade_quarantine(signals)
        assert "DOWNGRADE_MARKET_REALITY_FAILURE_PROMOTABLE" in codes

    def test_governance_block_ignored_fails(self):
        signals = [StrategyDowngradeSignal(
            signal_type=DowngradeSignalType.GOVERNANCE_BLOCK.value,
            signal_value=1.0,
            threshold=0.0,
            signal_detected=True,
        )]
        codes = validate_downgrade_quarantine(signals)
        assert "DOWNGRADE_GOVERNANCE_BLOCK_IGNORED" in codes

    def test_slippage_drift_over_threshold_fails(self):
        signals = [StrategyDowngradeSignal(
            signal_type=DowngradeSignalType.SLIPPAGE_DRIFT.value,
            signal_value=0.35,
            threshold=DEFAULT_SLIPPAGE_DRIFT_THRESHOLD,
            signal_detected=True,
        )]
        codes = validate_downgrade_quarantine(signals)
        assert "DOWNGRADE_SLIPPAGE_DRIFT_OVER_THRESHOLD" in codes

    def test_fill_rate_drift_over_threshold_fails(self):
        signals = [StrategyDowngradeSignal(
            signal_type=DowngradeSignalType.FILL_RATE_DRIFT.value,
            signal_value=0.25,
            threshold=DEFAULT_FILL_RATE_DRIFT_THRESHOLD,
            signal_detected=True,
        )]
        codes = validate_downgrade_quarantine(signals)
        assert "DOWNGRADE_FILL_RATE_DRIFT_OVER_THRESHOLD" in codes

    def test_regime_mismatch_promotable_fails(self):
        signals = [StrategyDowngradeSignal(
            signal_type=DowngradeSignalType.REGIME_MISMATCH.value,
            signal_value=1.0,
            threshold=0.0,
            signal_detected=True,
        )]
        codes = validate_downgrade_quarantine(signals)
        assert "DOWNGRADE_REGIME_MISMATCH_PROMOTABLE" in codes

    def test_ttl_expired_promotable_fails(self):
        signals = [StrategyDowngradeSignal(
            signal_type=DowngradeSignalType.STRATEGY_TTL_EXPIRED.value,
            signal_value=1.0,
            threshold=0.0,
            signal_detected=True,
        )]
        codes = validate_downgrade_quarantine(signals)
        assert "DOWNGRADE_TTL_EXPIRED_PROMOTABLE" in codes

    def test_stale_strategy_promotable_fails(self):
        signals = [StrategyDowngradeSignal(
            signal_type=DowngradeSignalType.VALIDATION_STALE.value,
            signal_value=1.0,
            threshold=0.0,
            signal_detected=True,
        )]
        codes = validate_downgrade_quarantine(signals)
        assert "DOWNGRADE_STALE_STRATEGY_PROMOTABLE" in codes


class TestNegativeTTL:
    def test_missing_ttl_fails(self):
        codes = validate_strategy_ttl_freshness(None, _make_policy())
        assert "STRATEGY_MISSING_TTL" in codes

    def test_missing_validation_timestamp_fails(self):
        refs = _make_valid_refs()
        refs.validation_snapshot_ts = ""
        codes = validate_strategy_ttl_freshness(refs, _make_policy())
        assert "STRATEGY_MISSING_VALIDATION_TIMESTAMP" in codes

    def test_expired_validation_fails(self):
        now = datetime.now(timezone.utc)
        refs = StrategyValidationEvidenceRef(
            r038a_passed=True, r038a_snapshot_ref="a",
            r038b_passed=True, r038b_snapshot_ref="b",
            r038c_passed=True, r038c_snapshot_ref="c",
            validation_snapshot_ts=(now - timedelta(days=200)).isoformat(),
            validation_snapshot_version="v1.0",
        )
        codes = validate_strategy_ttl_freshness(refs, _make_policy(validation_freshness_days=90))
        assert "STRATEGY_EXPIRED_VALIDATION" in codes

    def test_revalidation_before_live_missing_fails(self):
        refs = _make_valid_refs()
        codes = validate_strategy_ttl_freshness(refs, _make_policy(revalidation_required_before_live=False))
        assert "STRATEGY_REVALIDATION_BEFORE_LIVE_MISSING" in codes

    def test_unparseable_validation_expiry_ts_fails(self):
        refs = _make_valid_refs()
        refs.validation_expiry_ts = "not_a_valid_timestamp"
        codes = validate_strategy_ttl_freshness(refs, _make_policy())
        assert "STRATEGY_MISSING_VALIDATION_TIMESTAMP" in codes

    def test_expired_promotion_in_lifecycle_fails(self):
        past = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        request = _make_valid_promotion_request(promotion_expiry_ts=past)
        result = validate_strategy_lifecycle_governance(
            entry=_make_valid_entry(),
            request=request,
            policy=_make_policy(),
        )
        assert not result.validation_passed
        assert any("PROMOTION_EXPIRY_EXPIRED" in c for c in result.reason_codes)


class TestNegativeAllocation:
    def test_strategy_self_increases_capital_fails(self):
        entry = _make_valid_entry(real_capital=50000.0)
        result = validate_strategy_lifecycle_governance(entry=entry)
        assert not result.validation_passed
        assert any("NEW_STRATEGY_HAS_REAL_CAPITAL" in c for c in result.reason_codes)

    def test_risk_gate_cannot_veto_allocation_fails(self):
        policy = _make_policy(risk_gate_can_veto_allocation=False)
        codes = validate_strategy_ttl_freshness(_make_valid_refs(), policy)
        assert "ALLOCATION_RISK_GATE_CANNOT_VETO" in codes


class TestNegativeOverall:
    def test_promotion_request_none_fails_validation(self):
        codes = validate_promotion_readiness(None)
        assert "PROMOTION_MISSING_R038A_REF" in codes
        assert "PROMOTION_MISSING_R038B_REF" in codes
        assert "PROMOTION_MISSING_R038C_REF" in codes

    def test_live_boundary_none_fails(self):
        codes = validate_live_promotion_boundary(None)
        assert "PROMOTION_AUTO_LIVE_APPROVAL" in codes

    def test_gross_only_evidence_not_handled_here(self):
        request = _make_valid_promotion_request(net_of_cost_positive=False)
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_NET_OF_COST_NOT_POSITIVE" in codes

    def test_governance_block_prevents_promotion(self):
        signals = [StrategyDowngradeSignal(
            signal_type=DowngradeSignalType.GOVERNANCE_BLOCK.value,
            signal_value=1.0, threshold=0.0, signal_detected=True,
        )]
        result = validate_strategy_lifecycle_governance(
            entry=_make_valid_entry(),
            signals=signals,
            policy=_make_policy(),
        )
        assert not result.validation_passed

    def test_empty_registry_entry_fails_overall(self):
        result = validate_strategy_lifecycle_governance(
            entry=StrategyRegistryEntry(),
        )
        assert not result.validation_passed
        assert not result.registry_entry_valid

    def test_unparseable_expiry_ts_fails_full_lifecycle(self):
        refs = _make_valid_refs()
        refs.validation_expiry_ts = "not_a_valid_timestamp"
        entry = _make_valid_entry(validation_refs=refs)
        result = validate_strategy_lifecycle_governance(entry=entry)
        assert not result.validation_passed
        assert not result.transition_allowed
        assert not result.order_execution_allowed
        assert "STRATEGY_MISSING_VALIDATION_TIMESTAMP" in result.reason_codes


# ---- Boundary Tests ----

class TestBoundary:
    def test_ttl_exactly_threshold(self):
        request = _make_valid_promotion_request(
            strategy_ttl_remaining_days=DEFAULT_TTL_DAYS,
        )
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_TTL_EXPIRED" not in codes

    def test_validation_freshness_exactly_threshold(self):
        now = datetime.now(timezone.utc)
        refs = StrategyValidationEvidenceRef(
            r038a_passed=True, r038a_snapshot_ref="a",
            r038b_passed=True, r038b_snapshot_ref="b",
            r038c_passed=True, r038c_snapshot_ref="c",
            validation_snapshot_ts=now.isoformat(),
            validation_expiry_ts=(now + timedelta(days=DEFAULT_VALIDATION_FRESHNESS_DAYS)).isoformat(),
            validation_snapshot_version="v1.0",
        )
        codes = validate_strategy_ttl_freshness(refs, _make_policy())
        assert "STRATEGY_EXPIRED_VALIDATION" not in codes

    def test_promotion_expiry_exactly_threshold(self):
        now = datetime.now(timezone.utc)
        request = _make_valid_promotion_request(
            promotion_expiry_ts=(now + timedelta(days=DEFAULT_PROMOTION_EXPIRY_DAYS)).isoformat(),
        )
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_EXPIRY_EXPIRED" not in codes

    def test_slippage_drift_exactly_threshold(self):
        signals = [StrategyDowngradeSignal(
            signal_type=DowngradeSignalType.SLIPPAGE_DRIFT.value,
            signal_value=DEFAULT_SLIPPAGE_DRIFT_THRESHOLD,
            threshold=DEFAULT_SLIPPAGE_DRIFT_THRESHOLD,
            signal_detected=True,
        )]
        codes = validate_downgrade_quarantine(signals)
        assert "DOWNGRADE_SLIPPAGE_DRIFT_OVER_THRESHOLD" not in codes

    def test_fill_rate_drift_exactly_threshold(self):
        signals = [StrategyDowngradeSignal(
            signal_type=DowngradeSignalType.FILL_RATE_DRIFT.value,
            signal_value=DEFAULT_FILL_RATE_DRIFT_THRESHOLD,
            threshold=DEFAULT_FILL_RATE_DRIFT_THRESHOLD,
            signal_detected=True,
        )]
        codes = validate_downgrade_quarantine(signals)
        assert "DOWNGRADE_FILL_RATE_DRIFT_OVER_THRESHOLD" not in codes

    def test_drawdown_exactly_threshold(self):
        signals = [StrategyDowngradeSignal(
            signal_type=DowngradeSignalType.DRAWDOWN_BREACH.value,
            signal_value=DEFAULT_DRAWDOWN_BREACH_THRESHOLD,
            threshold=DEFAULT_DRAWDOWN_BREACH_THRESHOLD,
            signal_detected=True,
        )]
        codes = validate_downgrade_quarantine(signals)
        assert "DOWNGRADE_SIGNAL_IGNORED" in codes

    def test_shadow_allowed_only_as_recommendation(self):
        request = _make_valid_promotion_request(
            transition=PromotionTransition.RESEARCH_TO_SHADOW.value,
            deterministic_gate_result=True,
        )
        result = validate_strategy_lifecycle_governance(
            entry=_make_valid_entry(),
            request=request,
            policy=_make_policy(),
        )
        assert result.transition_allowed
        assert result.promotion_target == PromotionTransition.RESEARCH_TO_SHADOW.value

    def test_paper_allowed_only_as_recommendation(self):
        request = _make_valid_promotion_request(
            transition=PromotionTransition.RESEARCH_TO_SHADOW.value,
            current_stage=StrategyLifecycleStage.RESEARCH_ONLY.value,
        )
        result = validate_strategy_lifecycle_governance(
            entry=_make_valid_entry(),
            request=request,
            policy=_make_policy(),
        )
        assert result.transition_allowed
        assert result.promotion_target == PromotionTransition.RESEARCH_TO_SHADOW.value

    def test_paper_duration_from_r038c_refs_threshold(self):
        refs = _make_valid_refs()
        assert refs.validation_snapshot_version == "v1.0"

    def test_taiwan_liquidity_constraints_required_in_promotion(self):
        request = _make_valid_promotion_request(taiwan_constraints_acknowledged=False)
        codes = validate_promotion_readiness(request)
        assert "PROMOTION_TAIWAN_CONSTRAINTS_MISSING" in codes


# ---- Integration Tests ----

class TestIntegration:
    def test_cicd_pipeline_r038d_stage_passes(self):
        chain = CICDVerificationChain()
        stages = [
            {
                "type": "r038d_strategy_lifecycle",
                "name": R038D_STAGE_NAME,
                "entry": _make_valid_entry(),
                "request": _make_valid_promotion_request(),
            },
        ]
        result = chain.run_pipeline(stages)
        assert result.all_passed

    def test_cicd_pipeline_r038d_stage_fails_on_bad_entry(self):
        chain = CICDVerificationChain()
        stages = [
            {
                "type": "r038d_strategy_lifecycle",
                "name": "r038d_fail",
                "entry": StrategyRegistryEntry(),
            },
        ]
        result = chain.run_pipeline(stages)
        assert not result.stages[0].passed

    def test_cicd_pipeline_mixed_r038_stages(self):
        chain = CICDVerificationChain()
        stages = [
            {"type": "r038d_strategy_lifecycle", "name": "r038d_pass",
             "entry": _make_valid_entry()},
            {"type": "r038d_strategy_lifecycle", "name": "r038d_fail",
             "entry": StrategyRegistryEntry()},
        ]
        result = chain.run_pipeline(stages)
        assert not result.all_passed
        assert result.stages[0].passed
        assert not result.stages[1].passed

    def test_r038d_stage_name_constant(self):
        assert R038D_STAGE_NAME == "R038d_strategy_lifecycle"

    def test_strategy_lifecycle_status_enum(self):
        assert StrategyLifecycleStatus.REGISTERED.value == "registered"
        assert StrategyLifecycleStatus.QUARANTINED.value == "quarantined"

    def test_strategy_lifecycle_stage_enum(self):
        assert StrategyLifecycleStage.RESEARCH_ONLY.value == "research_only"
        assert StrategyLifecycleStage.LIVE_NORMAL.value == "live_normal"

    def test_promotion_transition_enum(self):
        assert PromotionTransition.RESEARCH_TO_SHADOW.value == "research_only_to_shadow"
        assert PromotionTransition.PAPER_TO_LIVE_SMALL.value == "paper_to_live_small"

    def test_downgrade_action_enum(self):
        assert DowngradeAction.DOWNGRADE_TO_RESEARCH_ONLY.value == "downgrade_to_research_only"
        assert DowngradeAction.QUARANTINE.value == "quarantine"

    def test_downgrade_signal_type_enum(self):
        assert DowngradeSignalType.DRAWDOWN_BREACH.value == "drawdown_breach"
        assert DowngradeSignalType.GOVERNANCE_BLOCK.value == "governance_block"

    def test_validation_result_defaults(self):
        r = StrategyLifecycleValidationResult()
        assert r.no_live_order_path
        assert not r.order_execution_allowed
        assert r.market_reality_required
        assert r.taiwan_constraints_required
        assert r.llm_cannot_approve_promotion
        assert r.risk_gate_can_veto_allocation

    def test_fail_closed_reason_codes_exist(self):
        assert isinstance(FAIL_CLOSED_REASON_CODES_R038D, dict)
        assert len(FAIL_CLOSED_REASON_CODES_R038D) >= 50
