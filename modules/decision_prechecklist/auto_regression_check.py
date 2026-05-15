from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from modules.decision_prechecklist.checklist import DecisionPreChecklist, PreChecklistResult
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


class AutoRegressionChecker:
    def __init__(self, checklist: DecisionPreChecklist | None = None):
        self._checklist = checklist or DecisionPreChecklist()

    def run(self, cases: list[FixedTestCase] | None = None) -> RegressionSuiteResult:
        target = cases if cases is not None else FIXED_TEST_CASES
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
        )
