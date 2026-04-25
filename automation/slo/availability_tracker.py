"""
R019 SLO - Availability Tracker

Tracks success rate and availability against SLO targets.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger("slo.availability")


@dataclass
class AvailabilitySLO:
    """Defines availability SLO target."""
    name: str
    target_success_rate: float  # 0.0-1.0
    target_uptime: float  # 0.0-1.0


class AvailabilityTracker:
    """Track success rate and availability."""

    def __init__(self):
        self._slos: Dict[str, AvailabilitySLO] = {}
        self._results: Dict[str, Dict[str, int]] = {}

    def register_slo(self, slo: AvailabilitySLO):
        """Register an availability SLO."""
        self._slos[slo.name] = slo
        self._results[slo.name] = {"success": 0, "failure": 0, "total": 0}
        logger.info(f"Registered availability SLO: {slo.name}")

    def record_result(self, operation: str, success: bool):
        """Record an operation result."""
        if operation not in self._results:
            self._results[operation] = {"success": 0, "failure": 0, "total": 0}
        self._results[operation]["total"] += 1
        if success:
            self._results[operation]["success"] += 1
        else:
            self._results[operation]["failure"] += 1

    def get_success_rate(self, operation: str) -> Optional[float]:
        """Calculate current success rate."""
        results = self._results.get(operation)
        if not results or results["total"] == 0:
            return None
        return results["success"] / results["total"]

    def check_slo(self, operation: str) -> Dict[str, Any]:
        """Check if operation meets availability SLO."""
        slo = self._slos.get(operation)
        if not slo:
            return {"status": "no_slo", "operation": operation}

        success_rate = self.get_success_rate(operation)
        results = self._results.get(operation, {"success": 0, "failure": 0, "total": 0})

        if success_rate is None:
            return {
                "operation": operation,
                "status": "no_data",
                "target": slo.target_success_rate,
            }

        meets_slo = success_rate >= slo.target_success_rate
        status = "meets_slo" if meets_slo else "below_slo"

        if not meets_slo:
            logger.warning(
                f"Availability SLO breach for {operation}: "
                f"{success_rate:.4f} < {slo.target_success_rate}"
            )

        return {
            "operation": operation,
            "status": status,
            "success_rate": success_rate,
            "target": slo.target_success_rate,
            "success_count": results["success"],
            "failure_count": results["failure"],
            "total_count": results["total"],
        }

    def get_all_status(self) -> Dict[str, Any]:
        """Return status for all registered SLOs."""
        return {
            op: self.check_slo(op)
            for op in self._slos.keys()
        }
