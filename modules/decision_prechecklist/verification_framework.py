from __future__ import annotations
import random
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable
from datetime import datetime, timezone


@dataclass
class VerificationCheck:
    name: str
    passed: bool
    detail: str = ""
    duration_ms: float = 0.0


@dataclass
class VerificationSuiteResult:
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    checks: list[VerificationCheck] = field(default_factory=list)
    started_at: str = ""
    ended_at: str = ""
    summary: str = ""

    @property
    def all_passed(self) -> bool:
        return self.failed_checks == 0


@dataclass
class StressTestScenario:
    name: str
    generate: Callable[[], Any]
    verify: Callable[[Any], bool]
    count: int = 100


@dataclass
class StressTestResult:
    scenario_name: str
    total: int
    passed: int
    failed: int
    pass_rate: float
    avg_duration_ms: float
    max_duration_ms: float
    min_duration_ms: float


class VerificationRunner:
    def __init__(self):
        self._checks: list[tuple[str, Callable[[], tuple[bool, str]]]] = []

    def add_check(self, name: str, fn: Callable[[], tuple[bool, str]]) -> None:
        self._checks.append((name, fn))

    def run_all(self) -> VerificationSuiteResult:
        started = datetime.now(timezone.utc).isoformat()
        checks: list[VerificationCheck] = []
        for name, fn in self._checks:
            t0 = datetime.now(timezone.utc)
            try:
                passed, detail = fn()
            except Exception as e:
                passed, detail = False, str(e)
            t1 = datetime.now(timezone.utc)
            elapsed = (t1 - t0).total_seconds() * 1000
            checks.append(VerificationCheck(
                name=name, passed=passed, detail=detail, duration_ms=elapsed,
            ))
        passed = sum(1 for c in checks if c.passed)
        failed = sum(1 for c in checks if not c.passed)
        return VerificationSuiteResult(
            total_checks=len(checks),
            passed_checks=passed,
            failed_checks=failed,
            checks=checks,
            started_at=started,
            ended_at=datetime.now(timezone.utc).isoformat(),
            summary=f"{passed}/{len(checks)} checks passed",
        )


class StressTestEngine:
    def __init__(self):
        self._scenarios: list[StressTestScenario] = []

    def add_scenario(self, scenario: StressTestScenario) -> None:
        self._scenarios.append(scenario)

    def run_scenario(self, scenario: StressTestScenario) -> StressTestResult:
        durations: list[float] = []
        passed = 0
        failed = 0
        for _ in range(scenario.count):
            t0 = datetime.now(timezone.utc)
            try:
                candidate = scenario.generate()
                ok = scenario.verify(candidate)
                if ok:
                    passed += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
            t1 = datetime.now(timezone.utc)
            durations.append((t1 - t0).total_seconds() * 1000)
        return StressTestResult(
            scenario_name=scenario.name,
            total=scenario.count,
            passed=passed,
            failed=failed,
            pass_rate=passed / max(scenario.count, 1),
            avg_duration_ms=statistics.mean(durations) if durations else 0,
            max_duration_ms=max(durations) if durations else 0,
            min_duration_ms=min(durations) if durations else 0,
        )

    def run_all(self) -> list[StressTestResult]:
        return [self.run_scenario(s) for s in self._scenarios]
