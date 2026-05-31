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
from modules.decision_prechecklist.strategy_lifecycle_governance import (
    StrategyRegistryEntry,
    StrategyPromotionRequest,
    StrategyDowngradeSignal,
    StrategyLifecyclePolicy,
    StrategyLifecycleValidationResult,
    STAGE_R038D,
    validate_strategy_lifecycle_governance,
    run_r038d_strategy_lifecycle,
)
from modules.decision_prechecklist.validation_metrics_ci_artifacts import (
    R038eMetricsCIArtifactsInput,
    R038eMetricsCIArtifactsResult,
    validate_metrics_ci_artifacts,
    run_r038e_metrics_ci_artifacts,
    STAGE_R038E,
)
from modules.decision_prechecklist.net_expected_advantage import (
    run_r038f_nea_confidence_calibration as _run_r038f,
    R038fNEAConfidenceCalibrationResult,
    STAGE_R038F,
)


R038A_STAGE_NAME = "R038a_market_reality_trace_replay"
R038B_STAGE_NAME = "R038b_l0_l4_validation_chain"
R038C_STAGE_NAME = "R038c_l5_l9_validation_chain"
R038D_STAGE_NAME = "R038d_strategy_lifecycle"
R038E_STAGE_NAME = "r038e_metrics_and_ci_artifacts"
R038F_STAGE_NAME = "r038f_nea_confidence_calibration"


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

    def validate_strategy_lifecycle_governance(
        self,
        entry: StrategyRegistryEntry | None = None,
        request: StrategyPromotionRequest | None = None,
        signals: list[StrategyDowngradeSignal] | None = None,
        policy: StrategyLifecyclePolicy | None = None,
    ) -> StrategyLifecycleValidationResult:
        return validate_strategy_lifecycle_governance(entry, request, signals, policy)

    def run_r038d_stage(
        self,
        entry: StrategyRegistryEntry | None = None,
        request: StrategyPromotionRequest | None = None,
        signals: list[StrategyDowngradeSignal] | None = None,
        policy: StrategyLifecyclePolicy | None = None,
    ) -> dict[str, Any]:
        return run_r038d_strategy_lifecycle(entry, request, signals, policy)

    def validate_r038e_metrics_ci_artifacts(
        self,
        input_data: R038eMetricsCIArtifactsInput,
    ) -> R038eMetricsCIArtifactsResult:
        result = validate_metrics_ci_artifacts(input_data)
        return result

    def run_r038e_stage(
        self,
        metrics: dict[str, Any],
        source_commit: str,
        source_branch: str,
        test_results: dict[str, Any],
        r038a_ref: str | None = None,
        r038b_ref: str | None = None,
        r038c_ref: str | None = None,
        r038d_ref: str | None = None,
        generated_at: str | None = None,
    ) -> R038eMetricsCIArtifactsResult:
        result = run_r038e_metrics_ci_artifacts(
            metrics=metrics,
            source_commit=source_commit,
            source_branch=source_branch,
            test_results=test_results,
            r038a_ref=r038a_ref,
            r038b_ref=r038b_ref,
            r038c_ref=r038c_ref,
            r038d_ref=r038d_ref,
            generated_at=generated_at,
        )
        return result

    def validate_r038f_nea_confidence_calibration(
        self,
        input_data: dict[str, Any],
    ) -> R038fNEAConfidenceCalibrationResult:
        return _run_r038f(
            p_hat=input_data.get("p_hat", 0.0),
            W_hat=input_data.get("W_hat", 0.0),
            L_hat=input_data.get("L_hat", 0.0),
            C=input_data.get("C", 0.0),
            S=input_data.get("S", 0.0),
            B=input_data.get("B", 0.0),
            T=input_data.get("T", 0.0),
            R=input_data.get("R", 0.0),
            U=input_data.get("U", 0.0),
            fill_probability=input_data.get("fill_probability", 0.0),
            regime_uncertainty=input_data.get("regime_uncertainty", 0.0),
            market_reality_snapshot=input_data.get("market_reality_snapshot"),
            risk_snapshot=input_data.get("risk_snapshot"),
            threshold_config_version=input_data.get("threshold_config_version"),
            calibration_version=input_data.get("calibration_version"),
            taiwan_reality_contract=input_data.get("taiwan_reality_contract"),
            order_execution_allowed=input_data.get("order_execution_allowed", False),
            calibration_brier_score=input_data.get("calibration_brier_score"),
            calibration_sample_count=input_data.get("calibration_sample_count", 0),
            calibration_timestamp=input_data.get("calibration_timestamp"),
            raw_confidence_not_used=input_data.get("raw_confidence_not_used", True),
            vetoes=input_data.get("vetoes"),
            llm_summary_only=input_data.get("llm_summary_only", True),
        )

    def run_r038f_stage(
        self,
        input_data: dict[str, Any],
    ) -> R038fNEAConfidenceCalibrationResult:
        return self.validate_r038f_nea_confidence_calibration(input_data)

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
                    elif stage_type == "r038d_strategy_lifecycle":
                        entry = s.get("entry")
                        req = s.get("request")
                        sigs = s.get("signals")
                        pol = s.get("policy")
                        result = self.validate_strategy_lifecycle_governance(entry, req, sigs, pol)
                        results.append(CICDStageResult(
                            name=s.get("name", R038D_STAGE_NAME),
                            passed=result.validation_passed,
                            detail=f"registry_valid={result.registry_entry_valid} "
                                   f"transition_allowed={result.transition_allowed} "
                                   f"reasons={result.reason_codes}",
                        ))
                    elif stage_type == "r038f_nea_confidence_calibration":
                        inp = s.get("input", {})
                        result = self.run_r038f_stage(inp)
                        results.append(CICDStageResult(
                            name=s.get("name", R038F_STAGE_NAME),
                            passed=result["pass_"],
                            detail=f"stage={result['stage']} "
                                   f"pass={result['pass_']} "
                                   f"net_edge={result['net_edge']:.4f} "
                                   f"payoff_bucket={result['payoff_bucket']} "
                                   f"reason_codes={len(result['reason_codes'])}",
                        ))
                    elif stage_type == "r038e_metrics_and_ci_artifacts":
                        metrics = s.get("metrics", {})
                        source_commit = s.get("source_commit", "unknown")
                        source_branch = s.get("source_branch", "unknown")
                        test_results = s.get("test_results", {})
                        r038a_ref = s.get("r038a_ref")
                        r038b_ref = s.get("r038b_ref")
                        r038c_ref = s.get("r038c_ref")
                        r038d_ref = s.get("r038d_ref")
                        gen_at = s.get("generated_at")
                        result = self.run_r038e_stage(
                            metrics=metrics,
                            source_commit=source_commit,
                            source_branch=source_branch,
                            test_results=test_results,
                            r038a_ref=r038a_ref,
                            r038b_ref=r038b_ref,
                            r038c_ref=r038c_ref,
                            r038d_ref=r038d_ref,
                            generated_at=gen_at,
                        )
                        results.append(CICDStageResult(
                            name=s.get("name", R038E_STAGE_NAME),
                            passed=result["pass_"],
                            detail=f"stage={result['stage']} "
                                   f"pass={result['pass_']} "
                                   f"reason_codes={len(result['reason_codes'])} "
                                   f"failed_metrics={len(result['failed_metric_names'])}",
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
