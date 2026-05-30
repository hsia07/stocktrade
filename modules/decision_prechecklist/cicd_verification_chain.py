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
from modules.decision_prechecklist.market_reality_trace_replay_contract import (
    DecisionTraceReplayInput,
    DecisionTraceReplayResult,
    ReplayValidationStatus,
    STAGE_R038A,
    validate_and_replay,
    run_r038a_market_reality_trace_replay,
)
from modules.decision_prechecklist.l0_l4_validation_chain import (
    L0L4ValidationInput,
    L0L4ValidationResult,
    L0L4ValidationStatus,
    STAGE_R038B,
    validate_l0_l4_chain,
    run_r038b_l0_l4_validation_chain,
)
from modules.decision_prechecklist.l5_l9_validation_chain import (
    L5L9ValidationInput,
    L5L9ValidationResult,
    L5L9ValidationStatus,
    STAGE_R038C,
    validate_l5_l9_chain,
    run_r038c_l5_l9_validation_chain,
)


R038A_STAGE_NAME = "R038a_market_reality_trace_replay"
R038B_STAGE_NAME = "R038b_l0_l4_validation_chain"
R038C_STAGE_NAME = "R038c_l5_l9_validation_chain"


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

    def validate_market_reality_trace_replay(
        self,
        input_data: DecisionTraceReplayInput,
        order_execution_allowed: bool = False,
    ) -> DecisionTraceReplayResult:
        return validate_and_replay(input_data, order_execution_allowed)

    def run_r038a_stage(
        self,
        input_data: DecisionTraceReplayInput,
        order_execution_allowed: bool = False,
    ) -> dict[str, Any]:
        return run_r038a_market_reality_trace_replay(input_data, order_execution_allowed)

    def validate_l0_l4_validation_chain(
        self,
        input_data: L0L4ValidationInput,
    ) -> L0L4ValidationResult:
        return validate_l0_l4_chain(input_data)

    def run_r038b_stage(
        self,
        input_data: L0L4ValidationInput,
    ) -> dict[str, Any]:
        return run_r038b_l0_l4_validation_chain(input_data)

    def validate_l5_l9_validation_chain(
        self,
        input_data: L5L9ValidationInput,
    ) -> L5L9ValidationResult:
        return validate_l5_l9_chain(input_data)

    def run_r038c_stage(
        self,
        input_data: L5L9ValidationInput,
    ) -> dict[str, Any]:
        return run_r038c_l5_l9_validation_chain(input_data)

    def run_pipeline(self, stages: list[dict[str, Any]] | None = None) -> CICDPipelineResult:
        if stages is not None:
            results: list[CICDStageResult] = []
            for s in stages:
                stage_type = s.get("type", "")
                try:
                    if stage_type == "r038a_market_reality":
                        inp = s.get("input")
                        oea = s.get("order_execution_allowed", False)
                        if inp is None:
                            inp = DecisionTraceReplayInput()
                        result = self.validate_market_reality_trace_replay(inp, oea)
                        results.append(CICDStageResult(
                            name=s.get("name", R038A_STAGE_NAME),
                            passed=result.replay_passed,
                            detail=f"status={result.status.value if result.status else 'unknown'} "
                                   f"reasons={result.reason_codes}",
                        ))
                    elif stage_type == "regression":
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
                    elif stage_type == "r038b_l0_l4":
                        inp = s.get("input")
                        if inp is None:
                            inp = L0L4ValidationInput()
                        result = self.validate_l0_l4_validation_chain(inp)
                        results.append(CICDStageResult(
                            name=s.get("name", R038B_STAGE_NAME),
                            passed=result.validation_passed,
                            detail=f"status={result.status.value if result.status else 'unknown'} "
                                   f"levels={result.levels_checked} "
                                   f"passed={result.passed_levels} "
                                   f"failed={result.failed_levels} "
                                   f"reasons={result.reason_codes}",
                        ))
                    elif stage_type == "r038c_l5_l9":
                        inp = s.get("input")
                        if inp is None:
                            inp = L5L9ValidationInput()
                        result = self.validate_l5_l9_validation_chain(inp)
                        results.append(CICDStageResult(
                            name=s.get("name", R038C_STAGE_NAME),
                            passed=result.validation_passed,
                            detail=f"status={result.status.value if result.status else 'unknown'} "
                                   f"levels={result.levels_checked} "
                                   f"passed={result.passed_levels} "
                                   f"failed={result.failed_levels} "
                                   f"reasons={result.reason_codes}",
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
