"""
R019 SLO - Latency Budget Manager

Tracks latency against defined budgets with alerting thresholds.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger("slo.latency")


@dataclass
class LatencyBudget:
    """Defines latency budget for an operation."""
    name: str
    p50_ms: float
    p95_ms: float
    p99_ms: float


class LatencyBudgetManager:
    """Track and enforce latency budgets."""

    def __init__(self):
        self._budgets: Dict[str, LatencyBudget] = {}
        self._measurements: Dict[str, List[float]] = {}

    def register_budget(self, budget: LatencyBudget):
        """Register a latency budget."""
        self._budgets[budget.name] = budget
        self._measurements[budget.name] = []
        logger.info(f"Registered latency budget: {budget.name}")

    def record(self, operation: str, latency_ms: float):
        """Record a latency measurement."""
        if operation not in self._measurements:
            self._measurements[operation] = []
        self._measurements[operation].append(latency_ms)

    def get_percentile(self, operation: str, percentile: float) -> Optional[float]:
        """Calculate percentile latency for an operation."""
        measurements = self._measurements.get(operation, [])
        if not measurements:
            return None
        sorted_ms = sorted(measurements)
        idx = int(len(sorted_ms) * percentile / 100)
        return sorted_ms[min(idx, len(sorted_ms) - 1)]

    def check_budget(self, operation: str) -> Dict[str, Any]:
        """Check if operation is within latency budget."""
        budget = self._budgets.get(operation)
        if not budget:
            return {"status": "no_budget", "operation": operation}

        p50 = self.get_percentile(operation, 50)
        p95 = self.get_percentile(operation, 95)
        p99 = self.get_percentile(operation, 99)

        violations = []
        if p50 and p50 > budget.p50_ms:
            violations.append(f"p50 exceeded: {p50:.2f}ms > {budget.p50_ms}ms")
        if p95 and p95 > budget.p95_ms:
            violations.append(f"p95 exceeded: {p95:.2f}ms > {budget.p95_ms}ms")
        if p99 and p99 > budget.p99_ms:
            violations.append(f"p99 exceeded: {p99:.2f}ms > {budget.p99_ms}ms")

        status = "violations" if violations else "within_budget"
        if violations:
            logger.warning(f"Latency budget violations for {operation}: {violations}")

        return {
            "operation": operation,
            "status": status,
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "budget": {
                "p50_ms": budget.p50_ms,
                "p95_ms": budget.p95_ms,
                "p99_ms": budget.p99_ms,
            },
            "violations": violations,
            "sample_count": len(self._measurements.get(operation, [])),
        }

    def get_all_status(self) -> Dict[str, Any]:
        """Return status for all registered budgets."""
        return {
            op: self.check_budget(op)
            for op in self._budgets.keys()
        }
