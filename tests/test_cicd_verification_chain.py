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


if __name__ == "__main__":
    import pytest; sys.exit(pytest.main([__file__, "-v"]))
