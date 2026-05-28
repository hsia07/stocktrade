from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any
from modules.decision_prechecklist.checklist import DecisionPreChecklist, TradeCandidate
from modules.decision_prechecklist.fixed_test_dataset import (
    FixedTestCase, FixedTestRunResult, FIXED_TEST_CASES,
)


@dataclass
class RegressionSuiteResult:
    total: int = 0
    matched: int = 0
    mismatched: int = 0
    results: list[FixedTestRunResult] = field(default_factory=list)
    summary: str = ""
    suite_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def as_report(self) -> dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "total": self.total,
            "matched": self.matched,
            "mismatched": self.mismatched,
            "passed": self.mismatched == 0 and self.total > 0,
            "summary": self.summary,
            "mismatch_items": [
                {
                    "test_name": r.test_name,
                    "expected_passed": r.expected_passed,
                    "actual_passed": r.actual_passed,
                    "expected_veto_code": r.expected_veto_code,
                    "actual_veto_code": r.actual_veto_code,
                    "matches_expectation": r.matches_expectation,
                }
                for r in self.results if not r.matches_expectation
            ],
            "all_results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "expected_passed": r.expected_passed,
                    "matches_expectation": r.matches_expectation,
                }
                for r in self.results
            ],
        }


class AutoRegressionChecker:
    def __init__(self, checklist: DecisionPreChecklist | None = None):
        self._checklist = checklist or DecisionPreChecklist()

    def run(self, cases: list[FixedTestCase] | None = None, *, mode: str = "full") -> RegressionSuiteResult:
        target = cases if cases is not None else FIXED_TEST_CASES
        if mode == "smoke":
            target = [
                c for c in target
                if "extreme" not in (c.name or "").lower()
                and "extreme" not in (c.description or "").lower()
            ]
        results: list[FixedTestRunResult] = []
        for case in target:
            actual = self._checklist.evaluate(case.candidate)
            matches = (
                actual.passed == case.expected_passed
                and (case.expected_veto_reason_code is None
                     or any(v["reason_code"] == case.expected_veto_reason_code for v in actual.vetoes))
            )
            actual_veto = actual.veto_reason_code
            results.append(FixedTestRunResult(
                test_name=case.name,
                passed=actual.passed,
                expected_passed=case.expected_passed,
                actual_passed=actual.passed,
                expected_veto_code=case.expected_veto_reason_code,
                actual_veto_code=actual_veto,
                matches_expectation=matches,
            ))
        matched = sum(1 for r in results if r.matches_expectation)
        mismatched = sum(1 for r in results if not r.matches_expectation)
        return RegressionSuiteResult(
            total=len(results),
            matched=matched,
            mismatched=mismatched,
            results=results,
            summary=f"{matched}/{len(results)} passed regression check",
            suite_name=f"R037_regression_{mode}",
        )

    def run_smoke(self, cases: list[FixedTestCase] | None = None) -> RegressionSuiteResult:
        return self.run(cases, mode="smoke")

    def check_strategy_parameter_update(self, candidate: TradeCandidate) -> dict[str, Any]:
        return {
            "contract": "strategy_parameter_update_regression_check",
            "status": "placeholder",
            "note": "Requires baseline strategy parameter snapshot for regression comparison. Not yet wired.",
        }

    def check_ai_weight_update(self, candidate: TradeCandidate) -> dict[str, Any]:
        return {
            "contract": "ai_weight_update_regression_check",
            "status": "placeholder",
            "note": "Requires baseline AI weight snapshot for regression comparison. Not yet wired.",
        }
