"""
R012 Latency Budget / AI Timeout Degradation — Decision Timing & Safety Foundation
Contract-only module. No real LLM provider calls. No runtime wiring. No state write.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class LatencyStatus(str, Enum):
    WITHIN_BUDGET = "within_budget"
    BUDGET_EXCEEDED = "budget_exceeded"
    TIMEOUT = "timeout"
    FAIL_CLOSED = "fail_closed"
    LOCAL_FALLBACK = "local_fallback"
    LLM_SKIPPED = "llm_skipped"


class DegradationReason(str, Enum):
    LATENCY_BUDGET_EXCEEDED = "LATENCY_BUDGET_EXCEEDED"
    AI_TIMEOUT = "AI_TIMEOUT"
    LLM_SUMMARY_SKIPPED = "LLM_SUMMARY_SKIPPED"
    LLM_FORMAT_ERROR = "LLM_FORMAT_ERROR"
    LLM_PROVIDER_ERROR = "LLM_PROVIDER_ERROR"
    LOCAL_DETERMINISTIC_FALLBACK_USED = "LOCAL_DETERMINISTIC_FALLBACK_USED"
    FAIL_CLOSED_NO_TRADE = "FAIL_CLOSED_NO_TRADE"
    ORDER_EXECUTION_ALLOWED_FALSE = "ORDER_EXECUTION_ALLOWED_FALSE"
    RISK_NOT_LOWERED = "RISK_NOT_LOWERED"
    REQUIRED_DATA_MISSING = "REQUIRED_DATA_MISSING"
    DETERMINISTIC_DECISION_SAFE = "DETERMINISTIC_DECISION_SAFE"


@dataclass
class LatencyBudget:
    """Budget definition for a single decision stage."""
    stage: str
    p99_ms: float
    timeout_ms: float
    description: str = ""


@dataclass
class DecisionLatencyMeasurement:
    """Recorded latency for a single decision stage."""
    trace_id: str
    stage: str
    elapsed_ms: float
    budget_ms: float
    timestamp: str
    status: str = ""
    reason_code: str = ""


@dataclass
class TimeoutPolicy:
    """Timeout policy for a decision pipeline."""
    ai_summary_timeout_ms: float = 500.0
    market_to_signal_p99_ms: float = 200.0
    decision_total_budget_ms: float = 1000.0
    fail_closed_on_ai_timeout: bool = True
    allow_local_fallback: bool = True


@dataclass
class DegradationDecision:
    """Result of a latency/timeout evaluation."""
    action: str
    order_execution_allowed: bool = False
    reason: str = ""
    risk_strength_unchanged: bool = True
    llm_summary_used: bool = False
    local_fallback_used: bool = False


@dataclass
class LatencyAuditEvent:
    """Audit event for latency/timeout/fallback. No secret values."""
    trace_id: str
    stage: str
    elapsed_ms: float
    budget_ms: float
    status: str
    reason_code: str
    timestamp: str
    action: str = ""


class LatencyBudgetRegistry:
    """
    Latency budget registry and evaluator.
    Contract-only: no real LLM provider calls, no runtime state write.
    """

    def __init__(self, timeout_policy: Optional[TimeoutPolicy] = None):
        self._policy = timeout_policy or TimeoutPolicy()
        self._measurements: List[DecisionLatencyMeasurement] = []
        self._audit_log: List[LatencyAuditEvent] = []
        self._budgets: Dict[str, LatencyBudget] = {}

    # ------------------------------------------------------------------
    # Budget Registry
    # ------------------------------------------------------------------

    def register_budget(self, budget: LatencyBudget) -> "LatencyBudgetRegistry":
        self._budgets[budget.stage] = budget
        return self

    def get_budget(self, stage: str) -> Optional[LatencyBudget]:
        return self._budgets.get(stage)

    # ------------------------------------------------------------------
    # Latency Recording
    # ------------------------------------------------------------------

    def record_latency(
        self,
        trace_id: str,
        stage: str,
        elapsed_ms: float,
    ) -> DecisionLatencyMeasurement:
        budget = self._budgets.get(stage)
        budget_ms = budget.p99_ms if budget else self._policy.decision_total_budget_ms
        status = (
            LatencyStatus.WITHIN_BUDGET.value
            if elapsed_ms <= budget_ms
            else LatencyStatus.BUDGET_EXCEEDED.value
        )
        reason = (
            DegradationReason.DETERMINISTIC_DECISION_SAFE
            if status == LatencyStatus.WITHIN_BUDGET.value
            else DegradationReason.LATENCY_BUDGET_EXCEEDED
        )
        measurement = DecisionLatencyMeasurement(
            trace_id=trace_id,
            stage=stage,
            elapsed_ms=elapsed_ms,
            budget_ms=budget_ms,
            timestamp=datetime.now().isoformat(),
            status=status,
            reason_code=reason.value,
        )
        self._measurements.append(measurement)
        self._audit_log.append(LatencyAuditEvent(
            trace_id=trace_id,
            stage=stage,
            elapsed_ms=elapsed_ms,
            budget_ms=budget_ms,
            status=status,
            reason_code=reason.value,
            timestamp=measurement.timestamp,
            action="record_latency",
        ))
        return measurement

    # ------------------------------------------------------------------
    # Budget Evaluation
    # ------------------------------------------------------------------

    def evaluate_latency_budget(self, stage: str, elapsed_ms: float) -> bool:
        """Return True if within budget, False if exceeded."""
        budget = self._budgets.get(stage)
        if not budget:
            return elapsed_ms <= self._policy.decision_total_budget_ms
        return elapsed_ms <= budget.p99_ms

    # ------------------------------------------------------------------
    # Timeout Evaluation
    # ------------------------------------------------------------------

    def evaluate_timeout(self, stage: str, elapsed_ms: float) -> bool:
        """Return True if timed out, False if within timeout."""
        budget = self._budgets.get(stage)
        timeout = budget.timeout_ms if budget else self._policy.ai_summary_timeout_ms
        return elapsed_ms > timeout

    # ------------------------------------------------------------------
    # Fail-Closed Fallback
    # ------------------------------------------------------------------

    def fail_closed_on_timeout(self, trace_id: str, stage: str) -> DegradationDecision:
        """Fail-closed decision: no trade, safe action, risk strength unchanged."""
        self._audit_log.append(LatencyAuditEvent(
            trace_id=trace_id,
            stage=stage,
            elapsed_ms=0.0,
            budget_ms=0.0,
            status=LatencyStatus.FAIL_CLOSED.value,
            reason_code=DegradationReason.FAIL_CLOSED_NO_TRADE.value,
            timestamp=datetime.now().isoformat(),
            action="fail_closed_on_timeout",
        ))
        return DegradationDecision(
            action="no_trade",
            order_execution_allowed=False,
            reason=DegradationReason.FAIL_CLOSED_NO_TRADE.value,
            risk_strength_unchanged=True,
            llm_summary_used=False,
            local_fallback_used=False,
        )

    # ------------------------------------------------------------------
    # Local Deterministic Fallback
    # ------------------------------------------------------------------

    def local_deterministic_fallback(
        self,
        trace_id: str,
        stage: str,
        required_data_present: bool = True,
    ) -> DegradationDecision:
        """
        Local deterministic fallback when LLM/API is unavailable.
        If required data missing → fail-closed no-trade.
        Otherwise → safe deterministic action (wait / reduce_risk / no_trade).
        Never enables order_execution_allowed.
        """
        if not required_data_present:
            self._audit_log.append(LatencyAuditEvent(
                trace_id=trace_id,
                stage=stage,
                elapsed_ms=0.0,
                budget_ms=0.0,
                status=LatencyStatus.FAIL_CLOSED.value,
                reason_code=DegradationReason.REQUIRED_DATA_MISSING.value,
                timestamp=datetime.now().isoformat(),
                action="local_fallback_required_data_missing",
            ))
            return DegradationDecision(
                action="no_trade",
                order_execution_allowed=False,
                reason=DegradationReason.REQUIRED_DATA_MISSING.value,
                risk_strength_unchanged=True,
                llm_summary_used=False,
                local_fallback_used=True,
            )

        self._audit_log.append(LatencyAuditEvent(
            trace_id=trace_id,
            stage=stage,
            elapsed_ms=0.0,
            budget_ms=0.0,
            status=LatencyStatus.LOCAL_FALLBACK.value,
            reason_code=DegradationReason.LOCAL_DETERMINISTIC_FALLBACK_USED.value,
            timestamp=datetime.now().isoformat(),
            action="local_deterministic_fallback",
        ))
        return DegradationDecision(
            action="wait",
            order_execution_allowed=False,
            reason=DegradationReason.LOCAL_DETERMINISTIC_FALLBACK_USED.value,
            risk_strength_unchanged=True,
            llm_summary_used=False,
            local_fallback_used=True,
        )

    # ------------------------------------------------------------------
    # Non-Blocking LLM Summary Boundary
    # ------------------------------------------------------------------

    def non_blocking_llm_summary_boundary(
        self,
        trace_id: str,
        llm_elapsed_ms: float,
        llm_success: bool = True,
        llm_format_valid: bool = True,
    ) -> DegradationDecision:
        """
        Evaluate LLM summary result within non-blocking boundary.
        LLM failure/timeout/format error → skip summary, use local fallback.
        LLM success but high confidence does NOT override risk gate.
        Never enables order_execution_allowed from LLM alone.
        """
        timed_out = self.evaluate_timeout("llm_summary", llm_elapsed_ms)

        if timed_out or not llm_success or not llm_format_valid:
            reason = (
                DegradationReason.AI_TIMEOUT if timed_out
                else DegradationReason.LLM_FORMAT_ERROR if not llm_format_valid
                else DegradationReason.LLM_PROVIDER_ERROR
            )
            self._audit_log.append(LatencyAuditEvent(
                trace_id=trace_id,
                stage="llm_summary",
                elapsed_ms=llm_elapsed_ms,
                budget_ms=self._policy.ai_summary_timeout_ms,
                status=LatencyStatus.LLM_SKIPPED.value,
                reason_code=reason.value,
                timestamp=datetime.now().isoformat(),
                action="llm_summary_skipped",
            ))
            # Non-blocking: use local deterministic fallback
            return self.local_deterministic_fallback(trace_id, "llm_summary")

        # LLM success within timeout — still does NOT enable order execution
        self._audit_log.append(LatencyAuditEvent(
            trace_id=trace_id,
            stage="llm_summary",
            elapsed_ms=llm_elapsed_ms,
            budget_ms=self._policy.ai_summary_timeout_ms,
            status=LatencyStatus.WITHIN_BUDGET.value,
            reason_code=DegradationReason.LLM_SUMMARY_SKIPPED.value,
            timestamp=datetime.now().isoformat(),
            action="llm_summary_present_but_non_blocking",
        ))
        return DegradationDecision(
            action="use_local_decision",
            order_execution_allowed=False,
            reason=DegradationReason.LLM_SUMMARY_SKIPPED.value,
            risk_strength_unchanged=True,
            llm_summary_used=True,
            local_fallback_used=False,
        )

    # ------------------------------------------------------------------
    # Safe Summary
    # ------------------------------------------------------------------

    def get_safe_summary(self) -> Dict[str, Any]:
        """Safe summary — no secret values, no API keys, no prompts."""
        return {
            "policy": {
                "ai_summary_timeout_ms": self._policy.ai_summary_timeout_ms,
                "market_to_signal_p99_ms": self._policy.market_to_signal_p99_ms,
                "decision_total_budget_ms": self._policy.decision_total_budget_ms,
                "fail_closed_on_ai_timeout": self._policy.fail_closed_on_ai_timeout,
                "allow_local_fallback": self._policy.allow_local_fallback,
            },
            "registered_budgets": len(self._budgets),
            "measurement_count": len(self._measurements),
            "audit_count": len(self._audit_log),
            "order_execution_allowed": False,
        }

    # ------------------------------------------------------------------
    # Audit / Trace
    # ------------------------------------------------------------------

    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Return latency audit events. Metadata only, no secret values."""
        return [
            {
                "trace_id": e.trace_id,
                "stage": e.stage,
                "elapsed_ms": e.elapsed_ms,
                "budget_ms": e.budget_ms,
                "status": e.status,
                "reason_code": e.reason_code,
                "timestamp": e.timestamp,
                "action": e.action,
            }
            for e in self._audit_log
        ]

    def get_last_event(self) -> Optional[Dict[str, Any]]:
        if not self._audit_log:
            return None
        e = self._audit_log[-1]
        return {
            "trace_id": e.trace_id,
            "stage": e.stage,
            "status": e.status,
            "reason_code": e.reason_code,
            "timestamp": e.timestamp,
        }

    # ------------------------------------------------------------------
    # Multiple Stage p99 Summary
    # ------------------------------------------------------------------

    def get_p99_summary(self) -> Dict[str, float]:
        """Return p99 summary per stage from recorded measurements."""
        from collections import defaultdict
        import statistics
        stage_times: Dict[str, List[float]] = defaultdict(list)
        for m in self._measurements:
            stage_times[m.stage].append(m.elapsed_ms)
        summary = {}
        for stage, times in stage_times.items():
            if times:
                sorted_times = sorted(times)
                idx = int(len(sorted_times) * 0.99)
                idx = min(idx, len(sorted_times) - 1)
                summary[stage] = sorted_times[idx]
        return summary

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def create_default_registry(cls) -> "LatencyBudgetRegistry":
        """Default registry with standard latency budgets (contract-level)."""
        policy = TimeoutPolicy(
            ai_summary_timeout_ms=500.0,
            market_to_signal_p99_ms=200.0,
            decision_total_budget_ms=1000.0,
            fail_closed_on_ai_timeout=True,
            allow_local_fallback=True,
        )
        reg = cls(timeout_policy=policy)
        reg.register_budget(LatencyBudget(
            stage="market_to_signal",
            p99_ms=200.0,
            timeout_ms=300.0,
            description="Market data to signal generation p99 budget",
        ))
        reg.register_budget(LatencyBudget(
            stage="llm_summary",
            p99_ms=400.0,
            timeout_ms=500.0,
            description="LLM summary generation timeout",
        ))
        reg.register_budget(LatencyBudget(
            stage="deterministic_decision",
            p99_ms=100.0,
            timeout_ms=150.0,
            description="Local deterministic decision budget",
        ))
        return reg
