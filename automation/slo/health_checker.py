"""
R019 SLO - Health Checker

Provides health check with threshold-based status determination.
"""

import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("slo.health")


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthThreshold:
    """Defines health thresholds for a metric."""
    name: str
    healthy_max: float
    degraded_max: float


class HealthChecker:
    """Check system health against thresholds."""

    def __init__(self):
        self._thresholds: Dict[str, HealthThreshold] = {}
        self._metrics: Dict[str, float] = {}

    def register_threshold(self, threshold: HealthThreshold):
        """Register a health threshold."""
        self._thresholds[threshold.name] = threshold
        logger.info(f"Registered health threshold: {threshold.name}")

    def record_metric(self, name: str, value: float):
        """Record a metric value."""
        self._metrics[name] = value

    def check_health(self, name: str) -> Dict[str, Any]:
        """Check health status for a metric."""
        threshold = self._thresholds.get(name)
        if not threshold:
            return {"status": "no_threshold", "metric": name}

        value = self._metrics.get(name)
        if value is None:
            return {
                "metric": name,
                "status": HealthStatus.UNHEALTHY.value,
                "reason": "no_data",
                "thresholds": {
                    "healthy_max": threshold.healthy_max,
                    "degraded_max": threshold.degraded_max,
                },
            }

        if value <= threshold.healthy_max:
            status = HealthStatus.HEALTHY
        elif value <= threshold.degraded_max:
            status = HealthStatus.DEGRADED
            logger.warning(f"Health degraded for {name}: {value}")
        else:
            status = HealthStatus.UNHEALTHY
            logger.error(f"Health unhealthy for {name}: {value}")

        return {
            "metric": name,
            "status": status.value,
            "value": value,
            "thresholds": {
                "healthy_max": threshold.healthy_max,
                "degraded_max": threshold.degraded_max,
            },
        }

    def get_overall_health(self) -> Dict[str, Any]:
        """Return overall system health."""
        checks = {
            name: self.check_health(name)
            for name in self._thresholds.keys()
        }

        statuses = [c["status"] for c in checks.values()]
        if any(s == HealthStatus.UNHEALTHY.value for s in statuses):
            overall = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED.value for s in statuses):
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return {
            "overall_status": overall.value,
            "checks": checks,
        }
