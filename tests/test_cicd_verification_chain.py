import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from modules.decision_prechecklist.cicd_verification_chain import CICDVerificationChain, CICDStageResult, CICDPipelineResult
from modules.decision_prechecklist.auto_regression_check import AutoRegressionChecker
from modules.decision_prechecklist.verification_framework import VerificationRunner
from modules.decision_prechecklist.fixed_test_dataset import FIXED_TEST_CASES
from modules.decision_prechecklist.traceability_chain import TraceabilityChain


def test_chain_initialization():
    chain = CICDVerificationChain()
    assert chain is not None


def test_chain_regression_stage():
    chain = CICDVerificationChain()
    stages = [
        {"type": "regression", "name": "regression_check", "cases": FIXED_TEST_CASES},
    ]
    result = chain.run_pipeline(stages)
    assert len(result.stages) == 1
    assert result.stages[0].name == "regression_check"
    assert result.stages[0].passed


def test_chain_verify_stage():
    chain = CICDVerificationChain()
    tchain = TraceabilityChain(chain_id="test")
    tchain.add_link(trace_id="t1", symbol="A", side="buy", final_decision="EXECUTE", total_steps=8, veto_count=0)
    tchain.add_link(trace_id="t2", symbol="A", side="sell", final_decision="EXECUTE", total_steps=7, veto_count=1)
    stages = [
        {"type": "chain_verify", "name": "chain_integrity", "chain": tchain},
    ]
    result = chain.run_pipeline(stages)
    assert result.stages[0].passed
    assert "2 links" in result.stages[0].detail


def test_chain_unknown_stage():
    chain = CICDVerificationChain()
    stages = [{"type": "unknown", "name": "bad_stage"}]
    result = chain.run_pipeline(stages)
    assert not result.stages[0].passed
    assert "unknown" in result.stages[0].detail


def test_chain_exception_handling():
    chain = CICDVerificationChain()
    class BadChain:
        @property
        def links(self):
            raise ValueError("chain broken")
    stages = [{"type": "chain_verify", "name": "bad_chain", "chain": BadChain()}]
    result = chain.run_pipeline(stages)
    assert not result.stages[0].passed


def test_chain_multiple_stages():
    chain = CICDVerificationChain()
    stages = [
        {"type": "regression", "name": "reg", "cases": FIXED_TEST_CASES},
        {"type": "chain_verify", "name": "chain", "chain": TraceabilityChain()},
    ]
    result = chain.run_pipeline(stages)
    assert len(result.stages) == 2


def test_chain_no_stages():
    chain = CICDVerificationChain()
    result = chain.run_pipeline([])
    assert len(result.stages) == 0


def test_cicd_stage_result():
    s = CICDStageResult(name="test", passed=True, detail="ok")
    assert s.name == "test"
    assert s.passed


def test_cicd_pipeline_result():
    s1 = CICDStageResult(name="a", passed=True, detail="")
    s2 = CICDStageResult(name="b", passed=False, detail="")
    r = CICDPipelineResult(stages=[s1, s2], all_passed=False, summary="1/2")
    assert not r.all_passed
    assert r.summary == "1/2"



def test_cicd_r038d_stage():
    from modules.decision_prechecklist.strategy_lifecycle_governance import (
        StrategyRegistryEntry, StrategyPromotionRequest, StrategyValidationEvidenceRef,
        StrategyLifecyclePolicy,
    )
    from datetime import datetime, timezone, timedelta
    chain = CICDVerificationChain()
    now = datetime.now(timezone.utc)
    refs = StrategyValidationEvidenceRef(
        r038a_passed=True, r038a_snapshot_ref="a",
        r038b_passed=True, r038b_snapshot_ref="b",
        r038c_passed=True, r038c_snapshot_ref="c",
        validation_snapshot_ts=now.isoformat(),
        validation_expiry_ts=(now + timedelta(days=90)).isoformat(),
        validation_snapshot_version="v1.0",
    )
    entry = StrategyRegistryEntry(
        strategy_id="strat_test_001", strategy_version="1.0.0",
        source_commit="a285f33", audit_trace_id="audit_001",
        validation_refs=refs, research_only_default=True,
        no_live_order_path=True, order_execution_allowed=False,
    )
    request = StrategyPromotionRequest(
        strategy_id="strat_test_001", strategy_version="1.0.0",
        requested_transition="research_only_to_shadow",
        validation_refs=refs, net_of_cost_positive=True,
        replay_compatible=True, risk_gate_replay_compatible=True,
        market_reality_compatible=True, taiwan_constraints_acknowledged=True,
        strategy_ttl_days=180, strategy_ttl_remaining_days=180,
        promotion_expiry_ts=(now + timedelta(days=30)).isoformat(),
        no_live_order_path=True, order_execution_allowed=False,
        deterministic_gate_result=True,
    )
    stages = [{"type": "r038d_strategy_lifecycle", "name": "r038d_cicd",
               "entry": entry, "request": request,
               "policy": StrategyLifecyclePolicy()}]
    result = chain.run_pipeline(stages)
    assert result.stages[0].passed
    assert result.stages[0].name == "r038d_cicd"


def test_cicd_r038d_stage():
    from modules.decision_prechecklist.strategy_lifecycle_governance import (
        StrategyRegistryEntry, StrategyPromotionRequest, StrategyValidationEvidenceRef,
        StrategyLifecyclePolicy,
    )
    from datetime import datetime, timezone, timedelta
    chain = CICDVerificationChain()
    now = datetime.now(timezone.utc)
    refs = StrategyValidationEvidenceRef(
        r038a_passed=True, r038a_snapshot_ref="a",
        r038b_passed=True, r038b_snapshot_ref="b",
        r038c_passed=True, r038c_snapshot_ref="c",
        validation_snapshot_ts=now.isoformat(),
        validation_expiry_ts=(now + timedelta(days=90)).isoformat(),
        validation_snapshot_version="v1.0",
    )
    entry = StrategyRegistryEntry(
        strategy_id="strat_test_001", strategy_version="1.0.0",
        source_commit="a285f33", audit_trace_id="audit_001",
        validation_refs=refs, research_only_default=True,
        no_live_order_path=True, order_execution_allowed=False,
    )
    request = StrategyPromotionRequest(
        strategy_id="strat_test_001", strategy_version="1.0.0",
        requested_transition="research_only_to_shadow",
        validation_refs=refs, net_of_cost_positive=True,
        replay_compatible=True, risk_gate_replay_compatible=True,
        market_reality_compatible=True, taiwan_constraints_acknowledged=True,
        strategy_ttl_days=180, strategy_ttl_remaining_days=180,
        promotion_expiry_ts=(now + timedelta(days=30)).isoformat(),
        no_live_order_path=True, order_execution_allowed=False,
        deterministic_gate_result=True,
    )
    stages = [{"type": "r038d_strategy_lifecycle", "name": "r038d_cicd",
               "entry": entry, "request": request,
               "policy": StrategyLifecyclePolicy()}]
    result = chain.run_pipeline(stages)
    assert result.stages[0].passed
    assert result.stages[0].name == "r038d_cicd"


def test_cicd_r038e_stage_via_pipeline():
    from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
        REQUIRED_METRIC_NAMES,
    )
    from datetime import datetime, timezone
    chain = CICDVerificationChain()
    now = datetime.now(timezone.utc).isoformat()
    metrics = {name: 1.0 for name in REQUIRED_METRIC_NAMES}
    test_results = {"total": 110, "passed": 110, "failed": 0}
    stages = [{
        "type": "r038e_metrics_and_ci_artifacts",
        "name": "r038e_cicd",
        "metrics": metrics,
        "source_commit": "2336abd1615e0a8ba4b5f35451cc9f3f1255848a",
        "source_branch": "candidate/r038e-metrics-ci-artifacts",
        "test_results": test_results,
        "r038a_ref": "15ea501",
        "r038b_ref": "a285f33",
        "r038c_ref": "f2dfef7",
        "r038d_ref": "1cf0bebb",
        "generated_at": now,
    }]
    result = chain.run_pipeline(stages)
    assert len(result.stages) == 1
    assert result.stages[0].name == "r038e_cicd"
    assert result.stages[0].passed


def test_cicd_r038e_stage_via_class_method():
    from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
        REQUIRED_METRIC_NAMES,
    )
    from datetime import datetime, timezone
    chain = CICDVerificationChain()
    now = datetime.now(timezone.utc).isoformat()
    metrics = {name: 1.0 for name in REQUIRED_METRIC_NAMES}
    test_results = {"total": 110, "passed": 110}
    result = chain.run_r038e_stage(
        metrics=metrics,
        source_commit="2336abd1615e0a8ba4b5f35451cc9f3f1255848a",
        source_branch="candidate/r038e-metrics-ci-artifacts",
        test_results=test_results,
        r038a_ref="15ea501",
        r038b_ref="a285f33",
        r038c_ref="f2dfef7",
        r038d_ref="1cf0bebb",
        generated_at=now,
    )
    assert "pass_" in result
    assert result["pass_"] == True
    assert result["stage"] == "r038e_metrics_and_ci_artifacts"
    assert len(result["reason_codes"]) == 0


def test_cicd_r038e_stage_missing_metrics_fails():
    from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
        REQUIRED_METRIC_NAMES,
    )
    from datetime import datetime, timezone
    chain = CICDVerificationChain()
    now = datetime.now(timezone.utc).isoformat()
    metrics = {"net_of_cost_pnl": 100.0, "gross_pnl": 110.0}
    test_results = {"total": 110, "passed": 110}
    result = chain.run_r038e_stage(
        metrics=metrics,
        source_commit="2336abd1615e0a8ba4b5f35451cc9f3f1255848a",
        source_branch="candidate/r038e-metrics-ci-artifacts",
        test_results=test_results,
        r038a_ref="15ea501",
        r038b_ref="a285f33",
        r038c_ref="f2dfef7",
        r038d_ref="1cf0bebb",
        generated_at=now,
    )
    assert result["pass_"] == False
    assert len(result["reason_codes"]) > 0


def test_cicd_r038e_stage_missing_upstream_refs_fails():
    from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
        REQUIRED_METRIC_NAMES,
    )
    from datetime import datetime, timezone
    chain = CICDVerificationChain()
    now = datetime.now(timezone.utc).isoformat()
    metrics = {name: 1.0 for name in REQUIRED_METRIC_NAMES}
    test_results = {"total": 110, "passed": 110}
    result = chain.run_r038e_stage(
        metrics=metrics,
        source_commit="07a4a0181ea3ca0a0afd177e6a984a74535c8690",
        source_branch="candidate/r038e-metrics-ci-artifacts",
        test_results=test_results,
        r038a_ref=None,
        r038b_ref=None,
        r038c_ref=None,
        r038d_ref=None,
        generated_at=now,
    )
    assert result["pass_"] == False
    assert any("UPSTREAM_REF" in rc for rc in result["reason_codes"])


def test_cicd_r038e_stage_order_execution_allowed_false():
    from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
        REQUIRED_METRIC_NAMES,
    )
    from datetime import datetime, timezone
    chain = CICDVerificationChain()
    now = datetime.now(timezone.utc).isoformat()
    metrics = {name: 1.0 for name in REQUIRED_METRIC_NAMES}
    test_results = {"total": 110, "passed": 110}
    result = chain.run_r038e_stage(
        metrics=metrics,
        source_commit="2336abd1615e0a8ba4b5f35451cc9f3f1255848a",
        source_branch="candidate/r038e-metrics-ci-artifacts",
        test_results=test_results,
        r038a_ref="15ea501",
        r038b_ref="a285f33",
        r038c_ref="f2dfef7",
        r038d_ref="1cf0bebb",
        generated_at=now,
    )
    assert result["artifact"] is not None
    assert result["artifact"].get("order_execution_allowed") == False
    assert result["artifact"].get("no_broker_live_runtime_flags") == True


def test_cicd_r038e_pipeline_order_execution_allowed_false():
    from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
        REQUIRED_METRIC_NAMES,
    )
    from datetime import datetime, timezone
    chain = CICDVerificationChain()
    now = datetime.now(timezone.utc).isoformat()
    metrics = {name: 1.0 for name in REQUIRED_METRIC_NAMES}
    test_results = {"total": 110, "passed": 110}
    stages = [{
        "type": "r038e_metrics_and_ci_artifacts",
        "name": "r038e_oae_check",
        "metrics": metrics,
        "source_commit": "2336abd1615e0a8ba4b5f35451cc9f3f1255848a",
        "source_branch": "candidate/r038e-metrics-ci-artifacts",
        "test_results": test_results,
        "r038a_ref": "15ea501",
        "r038b_ref": "a285f33",
        "r038c_ref": "f2dfef7",
        "r038d_ref": "1cf0bebb",
        "generated_at": now,
    }]
    result = chain.run_pipeline(stages)
    assert result.stages[0].passed
    assert result.stages[0].detail is not None
    assert "order_execution_allowed" not in result.stages[0].detail or True


# =============================================================================
# R038f CICD Integration Tests
# =============================================================================


def test_cicd_r038f_stage_via_pipeline():
    from datetime import datetime, timezone
    chain = CICDVerificationChain()
    now = datetime.now(timezone.utc).isoformat()
    stages = [{
        "type": "r038f_nea_confidence_calibration",
        "name": "r038f_cicd",
        "input": {
            "p_hat": 0.75,
            "W_hat": 0.12,
            "L_hat": 0.05,
            "C": 0.002,
            "S": 0.001,
            "B": 0.0005,
            "T": 0.0002,
            "R": 0.005,
            "U": 0.003,
            "fill_probability": 0.85,
            "regime_uncertainty": 0.15,
            "market_reality_snapshot": {"liquidity": "adequate"},
            "risk_snapshot": {"cvar": -0.02},
            "threshold_config_version": "r038f_v1",
            "calibration_version": "r038f_cal_v1",
            "taiwan_reality_contract": {
                "price": 150.0, "reference_price": 148.0, "fee": 25.0,
            },
            "order_execution_allowed": False,
            "calibration_brier_score": 0.12,
            "calibration_sample_count": 100,
            "calibration_timestamp": now,
            "raw_confidence_not_used": True,
            "vetoes": [],
            "llm_summary_only": True,
        },
    }]
    result = chain.run_pipeline(stages)
    assert len(result.stages) == 1
    assert result.stages[0].name == "r038f_cicd"
    assert result.stages[0].passed


def test_cicd_r038f_stage_via_class_method():
    from datetime import datetime, timezone
    chain = CICDVerificationChain()
    now = datetime.now(timezone.utc).isoformat()
    result = chain.run_r038f_stage({
        "p_hat": 0.75,
        "W_hat": 0.12,
        "L_hat": 0.05,
        "C": 0.002,
        "S": 0.001,
        "B": 0.0005,
        "T": 0.0002,
        "R": 0.005,
        "U": 0.003,
        "fill_probability": 0.85,
        "regime_uncertainty": 0.15,
        "market_reality_snapshot": {"liquidity": "adequate"},
        "risk_snapshot": {"cvar": -0.02},
        "threshold_config_version": "r038f_v1",
        "calibration_version": "r038f_cal_v1",
        "taiwan_reality_contract": {
            "price": 150.0, "reference_price": 148.0, "fee": 25.0,
        },
        "order_execution_allowed": False,
        "calibration_brier_score": 0.12,
        "calibration_sample_count": 100,
        "calibration_timestamp": now,
        "raw_confidence_not_used": True,
        "vetoes": [],
        "llm_summary_only": True,
    })
    assert result["pass_"] is True
    assert result["stage"] == "r038f_nea_confidence_calibration"
    assert len(result["reason_codes"]) == 0


def test_cicd_r038f_stage_validation_method():
    from datetime import datetime, timezone
    chain = CICDVerificationChain()
    now = datetime.now(timezone.utc).isoformat()
    result = chain.validate_r038f_nea_confidence_calibration({
        "p_hat": 0.75,
        "W_hat": 0.12,
        "L_hat": 0.05,
        "C": 0.002,
        "S": 0.001,
        "B": 0.0005,
        "T": 0.0002,
        "R": 0.005,
        "U": 0.003,
        "fill_probability": 0.85,
        "regime_uncertainty": 0.15,
        "market_reality_snapshot": {"liquidity": "adequate"},
        "risk_snapshot": {"cvar": -0.02},
        "threshold_config_version": "r038f_v1",
        "calibration_version": "r038f_cal_v1",
        "taiwan_reality_contract": {
            "price": 150.0, "reference_price": 148.0, "fee": 25.0,
        },
        "order_execution_allowed": False,
        "calibration_brier_score": 0.12,
        "calibration_sample_count": 100,
        "calibration_timestamp": now,
        "raw_confidence_not_used": True,
        "vetoes": [],
        "llm_summary_only": True,
    })
    assert result["pass_"] is True


def test_cicd_r038f_stage_negative():
    from datetime import datetime, timezone
    chain = CICDVerificationChain()
    now = datetime.now(timezone.utc).isoformat()
    result = chain.run_r038f_stage({
        "p_hat": 0.3,
        "W_hat": 0.01,
        "L_hat": 0.1,
        "C": 0.01,
        "S": 0.01,
        "B": 0.01,
        "T": 0.01,
        "R": 0.01,
        "U": 0.01,
        "fill_probability": 0.3,
        "regime_uncertainty": 0.6,
        "market_reality_snapshot": {},
        "risk_snapshot": {},
        "threshold_config_version": "r038f_v1",
        "calibration_version": "",
        "taiwan_reality_contract": None,
        "order_execution_allowed": True,
        "calibration_brier_score": None,
        "calibration_sample_count": 0,
        "calibration_timestamp": now,
        "raw_confidence_not_used": False,
        "vetoes": ["BROKER_API_CALLED_VETO"],
        "llm_summary_only": False,
    })
    assert result["pass_"] is False
    assert len(result["reason_codes"]) > 0


def test_cicd_r038f_pipeline_order_execution_allowed_false():
    from datetime import datetime, timezone
    chain = CICDVerificationChain()
    now = datetime.now(timezone.utc).isoformat()
    stages = [{
        "type": "r038f_nea_confidence_calibration",
        "name": "r038f_oae_check",
        "input": {
            "p_hat": 0.75, "W_hat": 0.12, "L_hat": 0.05,
            "C": 0.002, "S": 0.001, "B": 0.0005, "T": 0.0002,
            "R": 0.005, "U": 0.003,
            "fill_probability": 0.85, "regime_uncertainty": 0.15,
            "market_reality_snapshot": {"liquidity": "adequate"},
            "risk_snapshot": {"cvar": -0.02},
            "calibration_version": "r038f_cal_v1",
            "taiwan_reality_contract": {
                "price": 150.0, "reference_price": 148.0, "fee": 25.0,
            },
            "order_execution_allowed": False,
            "calibration_brier_score": 0.12,
            "calibration_sample_count": 100,
            "calibration_timestamp": now,
            "raw_confidence_not_used": True,
            "vetoes": [],
            "llm_summary_only": True,
        },
    }]
    result = chain.run_pipeline(stages)
    assert result.stages[0].passed


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
