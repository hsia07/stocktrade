"""
test_r012_latency_budget.py
R012 Latency Budget / AI Timeout Degradation Blocker Rework Test Suite.

All tests use in-memory dict-like measurements — NO real LLM provider calls,
NO real runtime state write, NO real DB, NO real .env dependency.
"""

import pytest
from pathlib import Path

from modules.latency_budget import (
    LatencyBudget,
    LatencyBudgetRegistry,
    TimeoutPolicy,
    DegradationDecision,
    LatencyStatus,
    DegradationReason,
)


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _make_registry() -> LatencyBudgetRegistry:
    """Standard test registry with latency budgets."""
    policy = TimeoutPolicy(
        ai_summary_timeout_ms=500.0,
        market_to_signal_p99_ms=200.0,
        decision_total_budget_ms=1000.0,
        fail_closed_on_ai_timeout=True,
        allow_local_fallback=True,
    )
    reg = LatencyBudgetRegistry(timeout_policy=policy)
    reg.register_budget(LatencyBudget(
        stage="market_to_signal", p99_ms=200.0, timeout_ms=300.0,
        description="Market to signal budget"
    ))
    reg.register_budget(LatencyBudget(
        stage="llm_summary", p99_ms=400.0, timeout_ms=500.0,
        description="LLM summary budget"
    ))
    reg.register_budget(LatencyBudget(
        stage="deterministic_decision", p99_ms=100.0, timeout_ms=150.0,
        description="Deterministic decision budget"
    ))
    return reg


# ═══════════════════════════════════════════════════════════════
# 1. Registry & Defaults
# ═══════════════════════════════════════════════════════════════

class TestLatencyBudgetRegistry:
    def test_latency_budget_registry_defaults(self):
        reg = LatencyBudgetRegistry.create_default_registry()
        assert reg.get_budget("market_to_signal") is not None
        assert reg.get_budget("llm_summary") is not None
        assert reg.get_budget("deterministic_decision") is not None

    def test_record_latency_measurement(self):
        reg = _make_registry()
        measurement = reg.record_latency("trace-1", "market_to_signal", 150.0)
        assert measurement.trace_id == "trace-1"
        assert measurement.stage == "market_to_signal"
        assert measurement.elapsed_ms == 150.0
        assert measurement.status == LatencyStatus.WITHIN_BUDGET.value


# ═══════════════════════════════════════════════════════════════
# 2. Market to Signal Budget
# ═══════════════════════════════════════════════════════════════

class TestMarketToSignalBudget:
    def test_market_to_signal_within_p99_budget_passes(self):
        reg = _make_registry()
        result = reg.record_latency("trace-1", "market_to_signal", 150.0)
        assert result.status == LatencyStatus.WITHIN_BUDGET.value
        assert result.reason_code == DegradationReason.DETERMINISTIC_DECISION_SAFE.value

    def test_market_to_signal_exceeds_p99_budget_blocks_trade(self):
        reg = _make_registry()
        result = reg.record_latency("trace-1", "market_to_signal", 250.0)
        assert result.status == LatencyStatus.BUDGET_EXCEEDED.value
        assert result.reason_code == DegradationReason.LATENCY_BUDGET_EXCEEDED.value


# ═══════════════════════════════════════════════════════════════
# 3. AI Summary Timeout
# ═══════════════════════════════════════════════════════════════

class TestAISummaryTimeout:
    def test_ai_summary_timeout_skips_summary_not_decision(self):
        reg = _make_registry()
        # LLM takes 600ms (exceeds 500ms timeout)
        decision = reg.non_blocking_llm_summary_boundary(
            "trace-1", llm_elapsed_ms=600.0, llm_success=True, llm_format_valid=True
        )
        # Decision should use local fallback, not block entirely
        assert decision.local_fallback_used is True
        assert decision.order_execution_allowed is False
        assert decision.reason in [
            DegradationReason.LOCAL_DETERMINISTIC_FALLBACK_USED.value,
            DegradationReason.REQUIRED_DATA_MISSING.value,
        ]

    def test_ai_summary_failure_is_non_blocking(self):
        reg = _make_registry()
        # LLM fails (success=False)
        decision = reg.non_blocking_llm_summary_boundary(
            "trace-1", llm_elapsed_ms=100.0, llm_success=False, llm_format_valid=True
        )
        # Should not crash; should use local fallback
        assert decision.local_fallback_used is True
        assert decision.order_execution_allowed is False


# ═══════════════════════════════════════════════════════════════
# 4. LLM Format / Provider Error → Local Fallback
# ═══════════════════════════════════════════════════════════════

class TestLLMErrorFallback:
    def test_llm_format_error_uses_local_deterministic_fallback(self):
        reg = _make_registry()
        decision = reg.non_blocking_llm_summary_boundary(
            "trace-1", llm_elapsed_ms=100.0, llm_success=True, llm_format_valid=False
        )
        assert decision.local_fallback_used is True
        assert decision.order_execution_allowed is False
        assert decision.risk_strength_unchanged is True

    def test_provider_quota_error_uses_local_deterministic_fallback(self):
        reg = _make_registry()
        # Simulate provider error by setting success=False
        decision = reg.non_blocking_llm_summary_boundary(
            "trace-1", llm_elapsed_ms=100.0, llm_success=False, llm_format_valid=True
        )
        assert decision.local_fallback_used is True
        assert decision.order_execution_allowed is False
        assert decision.risk_strength_unchanged is True


# ═══════════════════════════════════════════════════════════════
# 5. Local Deterministic Fallback
# ═══════════════════════════════════════════════════════════════

class TestLocalDeterministicFallback:
    def test_local_deterministic_fallback_no_trade_when_required_data_missing(self):
        reg = _make_registry()
        decision = reg.local_deterministic_fallback(
            "trace-1", "decision", required_data_present=False
        )
        assert decision.action == "no_trade"
        assert decision.order_execution_allowed is False
        assert decision.reason == DegradationReason.REQUIRED_DATA_MISSING.value

    def test_local_deterministic_fallback_does_not_enable_order_execution(self):
        reg = _make_registry()
        decision = reg.local_deterministic_fallback(
            "trace-1", "decision", required_data_present=True
        )
        assert decision.order_execution_allowed is False
        assert decision.action in ["wait", "no_trade", "reduce_risk"]
        assert decision.local_fallback_used is True


# ═══════════════════════════════════════════════════════════════
# 6. Fail-Closed
# ═══════════════════════════════════════════════════════════════

class TestFailClosed:
    def test_timeout_fail_closed_no_trade(self):
        reg = _make_registry()
        decision = reg.fail_closed_on_timeout("trace-1", "ai_summary")
        assert decision.action == "no_trade"
        assert decision.order_execution_allowed is False
        assert decision.reason == DegradationReason.FAIL_CLOSED_NO_TRADE.value
        assert decision.risk_strength_unchanged is True

    def test_timeout_reason_codes_present(self):
        reg = _make_registry()
        reg.fail_closed_on_timeout("trace-1", "ai_summary")
        log = reg.get_audit_log()
        assert len(log) >= 1
        last = log[-1]
        assert last["reason_code"] == DegradationReason.FAIL_CLOSED_NO_TRADE.value


# ═══════════════════════════════════════════════════════════════
# 7. Risk Strength
# ═══════════════════════════════════════════════════════════════

class TestRiskStrength:
    def test_risk_strength_not_lowered_on_timeout(self):
        reg = _make_registry()
        decision = reg.fail_closed_on_timeout("trace-1", "ai_summary")
        assert decision.risk_strength_unchanged is True

    def test_high_llm_confidence_cannot_override_risk_gate(self):
        reg = _make_registry()
        # Even if LLM is fast and successful, it cannot enable order execution
        decision = reg.non_blocking_llm_summary_boundary(
            "trace-1", llm_elapsed_ms=100.0, llm_success=True, llm_format_valid=True
        )
        assert decision.order_execution_allowed is False
        assert decision.risk_strength_unchanged is True
        # LLM summary may be present but non-blocking
        assert decision.llm_summary_used is True


# ═══════════════════════════════════════════════════════════════
# 8. Safe Summary / Audit
# ═══════════════════════════════════════════════════════════════

class TestSafeSummaryAndAudit:
    def test_safe_summary_has_no_secret_values(self):
        reg = _make_registry()
        summary = reg.get_safe_summary()
        assert "policy" in summary
        assert "order_execution_allowed" in summary
        assert summary["order_execution_allowed"] is False
        # No secret-like keys
        summary_str = str(summary)
        assert "api_key" not in summary_str.lower()
        assert "token" not in summary_str.lower()
        assert "password" not in summary_str.lower()
        assert "secret" not in summary_str.lower()

    def test_audit_trace_records_latency_timeout_fallback_metadata(self):
        reg = _make_registry()
        reg.record_latency("trace-1", "market_to_signal", 150.0)
        reg.fail_closed_on_timeout("trace-1", "ai_summary")
        log = reg.get_audit_log()
        assert len(log) >= 2
        for event in log:
            assert "trace_id" in event
            assert "stage" in event
            assert "status" in event
            assert "reason_code" in event
            assert "timestamp" in event

    def test_audit_trace_does_not_write_runtime_state(self):
        reg = _make_registry()
        reg.record_latency("trace-1", "market_to_signal", 150.0)
        # Audit is in-memory only; no file I/O or runtime state write
        import os
        assert not hasattr(reg, '_file_path') or reg._file_path is None


# ═══════════════════════════════════════════════════════════════
# 9. Order Execution / Broker / LLM Provider Contracts
# ═══════════════════════════════════════════════════════════════

class TestNoRealCalls:
    def test_order_execution_allowed_remains_false_contract(self):
        reg = _make_registry()
        # All decision paths must keep order_execution_allowed = False
        decision1 = reg.fail_closed_on_timeout("t1", "s1")
        decision2 = reg.local_deterministic_fallback("t2", "s2")
        decision3 = reg.non_blocking_llm_summary_boundary(
            "t3", 100.0, llm_success=True, llm_format_valid=True
        )
        decision4 = reg.non_blocking_llm_summary_boundary(
            "t4", 600.0, llm_success=False, llm_format_valid=True
        )
        for d in [decision1, decision2, decision3, decision4]:
            assert d.order_execution_allowed is False

    def test_no_broker_execution_live_import_or_call(self):
        import ast
        source = open("modules/latency_budget/latency_budget.py", "r", encoding="utf-8").read()
        tree = ast.parse(source)
        calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)
        forbidden = ['buy', 'sell', 'order', 'execute', 'broker', 'fubon', 'live']
        for f in forbidden:
            assert f not in calls, f"Forbidden call '{f}' found in source"

    def test_no_real_llm_provider_call(self):
        import ast
        source = open("modules/latency_budget/latency_budget.py", "r", encoding="utf-8").read()
        tree = ast.parse(source)
        calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.append(node.func.attr)
        # No real LLM provider calls
        llm_providers = ['openai', 'claude', 'gemini', 'ollama', 'openrouter', 'chatgpt', 'gpt']
        for provider in llm_providers:
            assert provider not in calls, f"LLM provider call '{provider}' found in source"


# ═══════════════════════════════════════════════════════════════
# 10. Total Budget / Multi-Stage / Idempotency
# ═══════════════════════════════════════════════════════════════

class TestTotalBudgetAndMultiStage:
    def test_decision_total_budget_exceeded_blocks_trade(self):
        reg = _make_registry()
        # Simulate total budget exceeded by checking evaluate_latency_budget
        # without a specific stage budget (uses total budget)
        within = reg.evaluate_latency_budget("unknown_stage", 900.0)
        exceeded = reg.evaluate_latency_budget("unknown_stage", 1100.0)
        assert within is True
        assert exceeded is False

    def test_multiple_stage_p99_summary(self):
        reg = _make_registry()
        reg.record_latency("t1", "market_to_signal", 100.0)
        reg.record_latency("t1", "market_to_signal", 150.0)
        reg.record_latency("t1", "market_to_signal", 200.0)
        reg.record_latency("t2", "llm_summary", 300.0)
        summary = reg.get_p99_summary()
        assert "market_to_signal" in summary
        assert "llm_summary" in summary
        # p99 of [100, 150, 200] = 200 (99th percentile of 3 items = index 2)
        assert summary["market_to_signal"] == 200.0

    def test_timeout_policy_idempotent(self):
        policy1 = TimeoutPolicy(ai_summary_timeout_ms=500.0)
        policy2 = TimeoutPolicy(ai_summary_timeout_ms=500.0)
        assert policy1.ai_summary_timeout_ms == policy2.ai_summary_timeout_ms
        assert policy1.fail_closed_on_ai_timeout == policy2.fail_closed_on_ai_timeout


# ═══════════════════════════════════════════════════════════════
# 11. Reason Codes
# ═══════════════════════════════════════════════════════════════

class TestReasonCodes:
    def test_reason_codes_for_latency_timeout_fallback(self):
        # Verify all required reason codes exist
        required = [
            DegradationReason.LATENCY_BUDGET_EXCEEDED,
            DegradationReason.AI_TIMEOUT,
            DegradationReason.LLM_SUMMARY_SKIPPED,
            DegradationReason.LOCAL_DETERMINISTIC_FALLBACK_USED,
            DegradationReason.FAIL_CLOSED_NO_TRADE,
            DegradationReason.ORDER_EXECUTION_ALLOWED_FALSE,
            DegradationReason.RISK_NOT_LOWERED,
        ]
        for reason in required:
            assert isinstance(reason.value, str)
            assert reason.value != ""


# ═══════════════════════════════════════════════════════════════
# 12. Runtime Wiring
# ═══════════════════════════════════════════════════════════════

class TestNoRuntimeWiring:
    def test_r012_foundation_not_runtime_wired(self):
        # Verify the module does not import or reference server/runtime wiring
        import ast
        source = open("modules/latency_budget/latency_budget.py", "r", encoding="utf-8").read()
        assert "server.py" not in source
        assert "runtime" not in source.lower() or "no runtime" in source.lower()
        assert "app.on_event" not in source
        assert "fastapi" not in source.lower()
