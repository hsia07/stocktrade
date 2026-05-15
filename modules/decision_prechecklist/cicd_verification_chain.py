from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable
from modules.decision_prechecklist.auto_regression_check import (
    AutoRegressionChecker, RegressionSuiteResult,
)
from modules.decision_prechecklist.verification_framework import (
    VerificationRunner, VerificationSuiteResult,
)
from modules.decision_prechecklist.traceability_chain import TraceabilityChain, ChainVerificationResult


@dataclass
class CICDStageResult:
    name: str
    passed: bool
    detail: str
    duration_ms: float = 0.0


@dataclass
class CICDPipelineResult:
    stages: list[CICDStageResult] = field(default_factory=list)
    all_passed: bool = False
    summary: str = ""


class CICDVerificationChain:
    def __init__(
        self,
        regression_checker: AutoRegressionChecker | None = None,
        verification_runner: VerificationRunner | None = None,
    ):
        self._regression = regression_checker or AutoRegressionChecker()
        self._verification = verification_runner or VerificationRunner()

    def run_pipeline(self, stages: list[dict[str, Any]] | None = None) -> CICDPipelineResult:
        if stages is not None:
            results: list[CICDStageResult] = []
            for s in stages:
                stage_type = s.get("type", "")
                try:
                    if stage_type == "regression":
                        cases = s.get("cases", None)
                        r = self._regression.run(cases)
                        results.append(CICDStageResult(
                            name=s.get("name", "regression"),
                            passed=r.mismatched == 0,
                            detail=r.summary,
                        ))
                    elif stage_type == "verification":
                        for check in s.get("checks", []):
                            self._verification.add_check(check["name"], check["fn"])
                        v = self._verification.run_all()
                        results.append(CICDStageResult(
                            name=s.get("name", "verification"),
                            passed=v.all_passed,
                            detail=v.summary,
                        ))
                    elif stage_type == "chain_verify":
                        chain: TraceabilityChain = s["chain"]
                        cv = chain.verify_chain()
                        results.append(CICDStageResult(
                            name=s.get("name", "chain_verify"),
                            passed=cv.valid,
                            detail=f"{cv.total_links} links verified",
                        ))
                    else:
                        results.append(CICDStageResult(
                            name=s.get("name", f"unknown_{stage_type}"),
                            passed=False,
                            detail=f"unknown stage type: {stage_type}",
                        ))
                except Exception as e:
                    results.append(CICDStageResult(
                        name=s.get("name", "error"),
                        passed=False,
                        detail=str(e),
                    ))
            all_pass = all(r.passed for r in results)
            return CICDPipelineResult(
                stages=results,
                all_passed=all_pass,
                summary=f"{sum(1 for r in results if r.passed)}/{len(results)} stages passed",
            )
        return CICDPipelineResult(all_passed=True, summary="no stages defined")
