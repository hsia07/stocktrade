from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable

from .nea_engine import NEAEngine
from .position_sizing import PositionSizingEngine
from .confidence_calibration import ConfidenceCalibrationGuard
from .replay_trace import ReplayTrace


SINGLE_SIGNAL_SOURCES = frozenset({
    "technical_indicator",
    "news_headline",
    "social_sentiment",
    "ai_score",
    "single_strategy",
})

EVENT_NEWS_SOCIAL_SOURCES = frozenset({
    "news_headline",
    "social_sentiment",
    "breaking_event",
    "unconfirmed_rumor",
    "event_driven",
})

SINGLE_SIGNAL_NON_EVENT_SOURCES = SINGLE_SIGNAL_SOURCES - EVENT_NEWS_SOCIAL_SOURCES


@dataclass
class TradeCandidate:
    symbol: str
    side: str
    quantity: int
    price: float
    signal_source: str
    confidence_raw: float
    strategy: str
    expected_return: float = 0.0
    cost_estimate: float = 0.0
    slippage_estimate: float = 0.0
    fill_probability: float = 1.0
    regime_uncertainty: float = 0.0
    risk_budget: float = 0.0
    current_exposure: float = 0.0
    portfolio_value: float = 0.0
    cash_available: float = 0.0
    t_plus_2_hold: float = 0.0
    avg_daily_volume: int = 0
    max_pct_of_volume: float = 0.01
    max_position_pct_of_portfolio: float = 0.05
    strategy_max_pct: float = 0.1
    regime_max_pct: float = 0.15
    historical_brier_score: float | None = None
    num_past_decisions: int = 0
    is_taiwan_stock: bool = False
    taiwan_price_limit_pct: float = 0.1
    is_collection_auction: bool = False
    is_odd_lot: bool = False
    is_suspended: bool = False
    is_disposition_stock: bool = False
    is_near_limit_up: bool = False
    is_near_limit_down: bool = False
    liquidity_score: float = 1.0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class PreChecklistResult:
    passed: bool
    veto: str | None
    veto_reason_code: str | None
    trace: ReplayTrace | None = None
    nea_result: Any = None
    sizing_result: Any = None
    calibration_result: Any = None
    vetoes: list[dict[str, str]] = field(default_factory=list)


class DecisionPreChecklist:
    def __init__(
        self,
        nea_engine: NEAEngine | None = None,
        sizing_engine: PositionSizingEngine | None = None,
        confidence_guard: ConfidenceCalibrationGuard | None = None,
        extra_veto_hook: Callable[[TradeCandidate], str | None] | None = None,
    ):
        self._nea = nea_engine or NEAEngine()
        self._sizing = sizing_engine or PositionSizingEngine()
        self._confidence = confidence_guard or ConfidenceCalibrationGuard()
        self._extra_veto_hook = extra_veto_hook

    def evaluate(self, candidate: TradeCandidate) -> PreChecklistResult:
        trace = ReplayTrace.new(candidate.symbol, candidate.side, f"{candidate.side.upper()} {candidate.quantity} @ {candidate.price}")
        vetoes: list[dict[str, str]] = []

        def _veto(gate: str, code: str, detail: str) -> None:
            vetoes.append({"gate": gate, "reason_code": code, "detail": detail})
            trace.add_veto(gate, code, detail)

        step_1 = self._check_single_signal(candidate)
        trace.add_step("single_signal_check", "BLOCKED" if step_1 else "PASS", f"source={candidate.signal_source}")
        if step_1:
            _veto("single_signal_gate", "SINGLE_SIGNAL_DIRECT_TRADE", f"source={candidate.signal_source} blocked single-signal direct trade")

        step_2 = self._check_llm_not_core(candidate)
        trace.add_step("llm_not_core_check", "BLOCKED" if step_2 else "PASS", "")
        if step_2:
            _veto("llm_gate", "LLM_IS_TRADE_CORE", "LLM/API required for trade release")

        step_3 = self._check_event_news_social(candidate)
        trace.add_step("event_news_social_check", "BLOCKED" if step_3 else "PASS", f"source={candidate.signal_source}")
        if step_3:
            _veto("event_news_social_gate", "HIGH_IMPACT_UNCONFIRMED_EVENT", "high-impact unconfirmed event: watch/no-trade/reduce-size only")

        step_4, market_reality_detail = self._check_market_reality(candidate)
        trace.add_step("market_reality_check", "BLOCKED" if step_4 else "PASS", market_reality_detail)
        if step_4:
            _veto("market_reality_gate", "MARKET_REALITY_FAIL", market_reality_detail)

        calibration_result = self._confidence.evaluate(
            raw_confidence=candidate.confidence_raw,
            historical_brier_score=candidate.historical_brier_score,
            num_past_decisions=candidate.num_past_decisions,
            regime_uncertainty=candidate.regime_uncertainty,
        )
        trace.add_step(
            "confidence_calibration",
            "BLOCKED" if calibration_result.veto_reason else "PASS",
            f"raw={candidate.confidence_raw:.4f} calibrated={calibration_result.calibrated_confidence:.4f}",
        )
        if calibration_result.veto_reason:
            _veto("confidence_calibration_gate", "CONFIDENCE_CALIBRATION_FAIL", calibration_result.veto_reason)

        nea_result = self._nea.calculate(
            symbol=candidate.symbol,
            side=candidate.side,
            price=candidate.price,
            quantity=candidate.quantity,
            expected_return=candidate.expected_return,
            cost_estimate=candidate.cost_estimate,
            slippage_estimate=candidate.slippage_estimate,
            fill_probability=candidate.fill_probability,
            regime_uncertainty=candidate.regime_uncertainty,
        )
        trace.add_step("nea_check", "BLOCKED" if not nea_result.passed else "PASS", nea_result.veto_reason)
        if not nea_result.passed:
            _veto("nea_gate", "NEA_FAIL", nea_result.veto_reason)

        step_6 = self._check_taiwan_constraints(candidate)
        trace.add_step("taiwan_constraints_check", "BLOCKED" if step_6 else "PASS", step_6 or "")
        if step_6:
            _veto("taiwan_gate", "TAIWAN_CONSTRAINT", step_6)

        if self._extra_veto_hook:
            extra_reason = self._extra_veto_hook(candidate)
            if extra_reason:
                trace.add_step("extra_veto_hook", "BLOCKED", extra_reason)
                _veto("extra_veto_gate", "EXTRA_VETO", extra_reason)

        risk_snapshot = {
            "risk_budget": candidate.risk_budget,
            "current_exposure": candidate.current_exposure,
            "cash_available": candidate.cash_available,
            "t_plus_2_hold": candidate.t_plus_2_hold,
        }
        trace.risk_snapshot = risk_snapshot

        if not vetoes:
            sizing_result = self._sizing.calculate(
                symbol=candidate.symbol,
                side=candidate.side,
                price=candidate.price,
                confidence_calibrated=calibration_result.calibrated_confidence,
                risk_budget=candidate.risk_budget,
                current_exposure=candidate.current_exposure,
                portfolio_value=candidate.portfolio_value,
                strategy_max_pct=candidate.strategy_max_pct,
                regime_max_pct=candidate.regime_max_pct,
                cash_available=candidate.cash_available,
                t_plus_2_hold=candidate.t_plus_2_hold,
                avg_daily_volume=candidate.avg_daily_volume,
                max_pct_of_volume=candidate.max_pct_of_volume,
                max_position_pct_of_portfolio=candidate.max_position_pct_of_portfolio,
            )
            trace.add_step(
                "position_sizing",
                "BLOCKED" if not sizing_result.passed else "PASS",
                sizing_result.veto_reason,
            )
            if not sizing_result.passed:
                _veto("position_sizing_gate", "SIZING_FAIL", sizing_result.veto_reason)

            final_decision = "PASS"
            if nea_result.passed and not vetoes:
                final_decision = "EXECUTE" if sizing_result.final_qty > 0 else "PASS_NO_TRADE"
            else:
                final_decision = "BLOCKED"
        else:
            sizing_result = None
            final_decision = "BLOCKED"

        trace.finalize(final_decision)
        trace.market_reality_snapshot = {
            "fill_probability": candidate.fill_probability,
            "slippage_estimate": candidate.slippage_estimate,
            "cost_estimate": candidate.cost_estimate,
        }

        overall_passed = final_decision in ("EXECUTE", "PASS_NO_TRADE") and not vetoes
        main_veto = vetoes[0] if vetoes else None

        return PreChecklistResult(
            passed=overall_passed,
            veto=main_veto["detail"] if main_veto else None,
            veto_reason_code=main_veto["reason_code"] if main_veto else None,
            trace=trace,
            nea_result=nea_result,
            sizing_result=sizing_result,
            calibration_result=calibration_result,
            vetoes=vetoes,
        )

    def _check_single_signal(self, candidate: TradeCandidate) -> str | None:
        if candidate.signal_source in SINGLE_SIGNAL_NON_EVENT_SOURCES:
            return f"single signal source '{candidate.signal_source}' cannot directly trigger trade"
        return None

    def _check_llm_not_core(self, candidate: TradeCandidate) -> str | None:
        src = candidate.signal_source.lower() if candidate.signal_source else ""
        if "llm" in src or "api" in src:
            return f"source '{candidate.signal_source}' requires LLM/API for trade release"
        return None

    def _check_event_news_social(self, candidate: TradeCandidate) -> str | None:
        if candidate.signal_source in EVENT_NEWS_SOCIAL_SOURCES:
            return (
                f"high-impact unconfirmed event source '{candidate.signal_source}': "
                "watch/no-trade/reduce-size/wait-confirmation/tighten-risk only"
            )
        return None

    def _check_market_reality(self, candidate: TradeCandidate) -> tuple[str | None, str]:
        issues = []
        if candidate.cost_estimate < 0:
            issues.append("negative cost estimate")
        if candidate.slippage_estimate < 0:
            issues.append("negative slippage estimate")
        if candidate.fill_probability < 0.01:
            issues.append(f"fill_probability too low: {candidate.fill_probability:.4f}")
        if candidate.price <= 0:
            issues.append(f"non-positive price: {candidate.price}")
        detail = "; ".join(issues) if issues else "market reality check pass"
        return (detail if issues else None, detail)

    def _check_taiwan_constraints(self, candidate: TradeCandidate) -> str | None:
        if not candidate.is_taiwan_stock:
            return None
        issues = []
        if candidate.is_suspended:
            issues.append("stock suspended")
        if candidate.is_disposition_stock:
            issues.append("disposition stock restricted")
        if candidate.is_near_limit_up:
            issues.append(f"near limit up (within {candidate.taiwan_price_limit_pct*100:.0f}%)")
        if candidate.is_near_limit_down:
            issues.append(f"near limit down (within {candidate.taiwan_price_limit_pct*100:.0f}%)")
        if candidate.liquidity_score < 0.3:
            issues.append(f"liquidity insufficient: score={candidate.liquidity_score:.2f}")
        if candidate.is_collection_auction:
            issues.append("collection auction session")
        if not issues:
            return None
        return "; ".join(issues)
