from __future__ import annotations
import logging
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger("Core-A-Shadow")

_IMPORT_ERRORS: dict[str, str] = {}


def _safe_import(module_path: str, name: str):
    try:
        return __import__(module_path, fromlist=[name])
    except Exception as e:
        _IMPORT_ERRORS[module_path] = str(e)
        return None


_R027_MOD = _safe_import("modules.strategy.arbitrage_protection", "ArbitrageProtection")
_R027_GATE = _safe_import("modules.risk.arbitrage_risk_gate", "ArbitrageRiskGate")
_R027_SLIP = _safe_import("modules.market_reality.arbitrage_slippage_model", "ArbitrageSlippageModel")
_R028_MOD = _safe_import("modules.market_reality.layer", "MarketRealityLayer")
_R029_COST = _safe_import("modules.market_reality.cost_tracking", "CostTracker")
_R029_SLIP = _safe_import("modules.market_reality.slippage_monitor", "SlippageMonitor")
_R029_FILL = _safe_import("modules.market_reality.fill_probability", "FillProbabilityModel")
_R029_INTG = _safe_import("modules.market_reality.integration", "MarketRealityIntegration")
_R030_MOD = _safe_import("modules.decision_prechecklist.checklist", "DecisionPreCheckList")
_R030_TDC = _safe_import("modules.decision_prechecklist.checklist", "TradeCandidate")
_R031_MOD = _safe_import("modules.decision_prechecklist.confidence_decomposition", "ConfidenceSourceDecomposer")
_R032_MOD = _safe_import("modules.decision_prechecklist.traceability_chain", "TraceabilityChain")
_R034_MOD = _safe_import("modules.decision_prechecklist.replay_isolation", "ReplayIsolationGate")
_R035_MOD = _safe_import("modules.decision_prechecklist.verification_framework", "VerificationRunner")
_R043_MOD = _safe_import("modules.decision_prechecklist.news_analyzer", "NewsAnalyzer")
_R044_MOD = _safe_import("modules.decision_prechecklist.event_deduplicator", "EventDeduplicator")
_R045_MOD = _safe_import("modules.decision_prechecklist.event_importance_scorer", "EventImportanceScorer")
_R046_MOD = _safe_import("modules.decision_prechecklist.conflict_integrator", "ConflictIntegrator")
_R047_MOD = _safe_import("modules.decision_prechecklist.execution_sizing_guard", "ExecutionSizingGuard")
_R047_SLP = _safe_import("modules.decision_prechecklist.execution_sizing_guard", "SlippageEstimator")
_R048_MOD = _safe_import("modules.decision_prechecklist.microstructure_engine", "MicrostructureEngine")

_ArbitrageProtection = getattr(_R027_MOD, "ArbitrageProtection", None) if _R027_MOD else None
_ArbitrageRiskGate = getattr(_R027_GATE, "ArbitrageRiskGate", None) if _R027_GATE else None
_ArbitrageSlippageModel = getattr(_R027_SLIP, "ArbitrageSlippageModel", None) if _R027_SLIP else None
_MarketRealityLayer = getattr(_R028_MOD, "MarketRealityLayer", None) if _R028_MOD else None
_CostTracker = getattr(_R029_COST, "CostTracker", None) if _R029_COST else None
_SlippageMonitor = getattr(_R029_SLIP, "SlippageMonitor", None) if _R029_SLIP else None
_FillProbabilityModel = getattr(_R029_FILL, "FillProbabilityModel", None) if _R029_FILL else None
_MarketRealityIntegration = getattr(_R029_INTG, "MarketRealityIntegration", None) if _R029_INTG else None
_DecisionPreCheckList = getattr(_R030_MOD, "DecisionPreCheckList", None) if _R030_MOD else None
_TradeCandidate = getattr(_R030_TDC, "TradeCandidate", None) if _R030_TDC else None
_ConfidenceSourceDecomposer = getattr(_R031_MOD, "ConfidenceSourceDecomposer", None) if _R031_MOD else None
_TraceabilityChain = getattr(_R032_MOD, "TraceabilityChain", None) if _R032_MOD else None
_ReplayIsolationGate = getattr(_R034_MOD, "ReplayIsolationGate", None) if _R034_MOD else None
_VerificationRunner = getattr(_R035_MOD, "VerificationRunner", None) if _R035_MOD else None
_NewsAnalyzer = getattr(_R043_MOD, "NewsAnalyzer", None) if _R043_MOD else None
_EventDeduplicator = getattr(_R044_MOD, "EventDeduplicator", None) if _R044_MOD else None
_EventImportanceScorer = getattr(_R045_MOD, "EventImportanceScorer", None) if _R045_MOD else None
_ConflictIntegrator = getattr(_R046_MOD, "ConflictIntegrator", None) if _R046_MOD else None
_ExecutionSizingGuard = getattr(_R047_MOD, "ExecutionSizingGuard", None) if _R047_MOD else None
_SlippageEstimator = getattr(_R047_SLP, "SlippageEstimator", None) if _R047_SLP else None
_MicrostructureEngine = getattr(_R048_MOD, "MicrostructureEngine", None) if _R048_MOD else None


@dataclass
class CoreAShadowSnapshot:
    trace_id: str = ""
    timestamp: str = ""
    symbol: str = ""
    input_summary: dict = field(default_factory=dict)
    precheck_summary: dict | None = None
    veto_summary: dict | None = None
    market_reality_summary: dict | None = None
    sizing_summary: dict | None = None
    microstructure_summary: dict | None = None
    event_summary: dict | None = None
    confidence_summary: dict | None = None
    shadow_result: str = "available"
    vetoes: list[dict] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    source_versions: dict = field(default_factory=dict)
    no_order_side_effects: bool = True
    order_execution_allowed: bool = False


_SOURCE_VERSIONS: dict[str, str] = {
    "R027": "ArbitrageProtection" if _ArbitrageProtection else "UNAVAILABLE",
    "R028": "MarketRealityLayer" if _MarketRealityLayer else "UNAVAILABLE",
    "R029": "CostTracker+SlippageMonitor+FillProbability" if _CostTracker else "UNAVAILABLE",
    "R030": "DecisionPreCheckList" if _DecisionPreCheckList else "UNAVAILABLE",
    "R031": "ConfidenceSourceDecomposer" if _ConfidenceSourceDecomposer else "UNAVAILABLE",
    "R032": "TraceabilityChain" if _TraceabilityChain else "UNAVAILABLE",
    "R034": "ReplayIsolationGate" if _ReplayIsolationGate else "UNAVAILABLE",
    "R035": "VerificationRunner" if _VerificationRunner else "UNAVAILABLE",
    "R043": "NewsAnalyzer" if _NewsAnalyzer else "UNAVAILABLE",
    "R044": "EventDeduplicator" if _EventDeduplicator else "UNAVAILABLE",
    "R045": "EventImportanceScorer" if _EventImportanceScorer else "UNAVAILABLE",
    "R046": "ConflictIntegrator" if _ConflictIntegrator else "UNAVAILABLE",
    "R047": "ExecutionSizingGuard" if _ExecutionSizingGuard else "UNAVAILABLE",
    "R048": "MicrostructureEngine" if _MicrostructureEngine else "UNAVAILABLE",
}


class CoreAShadowAggregator:
    def __init__(self):
        self._layer: Any = _MarketRealityLayer() if _MarketRealityLayer else None
        self._cost: Any = _CostTracker() if _CostTracker else None
        self._slippage_mon: Any = _SlippageMonitor() if _SlippageMonitor else None
        self._fill: Any = _FillProbabilityModel() if _FillProbabilityModel else None
        self._integration: Any = _MarketRealityIntegration() if _MarketRealityIntegration else None
        self._precheck: Any = _DecisionPreCheckList() if _DecisionPreCheckList else None
        self._confidence: Any = _ConfidenceSourceDecomposer() if _ConfidenceSourceDecomposer else None
        self._trace: Any = _TraceabilityChain() if _TraceabilityChain else None
        self._replay: Any = _ReplayIsolationGate() if _ReplayIsolationGate else None
        self._verify: Any = _VerificationRunner() if _VerificationRunner else None
        self._news: Any = _NewsAnalyzer() if _NewsAnalyzer else None
        self._dedup: Any = _EventDeduplicator() if _EventDeduplicator else None
        self._scorer: Any = _EventImportanceScorer() if _EventImportanceScorer else None
        self._conflict: Any = _ConflictIntegrator() if _ConflictIntegrator else None
        self._sizing: Any = _ExecutionSizingGuard() if _ExecutionSizingGuard else None
        self._micro: Any = _MicrostructureEngine() if _MicrostructureEngine else None
        self._arb_protection: Any = None
        self._arb_gate: Any = None
        self._arb_slip: Any = None
        if _ArbitrageProtection and _ArbitrageRiskGate and _ArbitrageSlippageModel:
            self._arb_gate = _ArbitrageRiskGate(position_limit=100, exposure_limit=100000, loss_limit=5000)
            self._arb_slip = _ArbitrageSlippageModel()
            self._arb_protection = _ArbitrageProtection(risk_gate=self._arb_gate, market_reality_model=self._arb_slip)
        self._trace_id_counter: int = 0

    def evaluate(self, symbol: str, bars: list, tick: dict, open_positions: dict | None = None) -> CoreAShadowSnapshot:
        try:
            return self._build_snapshot(symbol, bars, tick, open_positions or {})
        except Exception as exc:
            log.error("Core-A Shadow evaluate failed for %s: %s", symbol, exc)
            return self._unavailable_snapshot(symbol, str(exc))

    def _unavailable_snapshot(self, symbol: str, reason: str) -> CoreAShadowSnapshot:
        self._trace_id_counter += 1
        return CoreAShadowSnapshot(
            trace_id=f"core_a_{int(time.time() * 1000)}_{self._trace_id_counter}",
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            input_summary={},
            shadow_result="unavailable",
            reasons=[f"Shadow evaluation unavailable: {reason}"],
            warnings=[],
            source_versions=_SOURCE_VERSIONS,
            no_order_side_effects=True,
            order_execution_allowed=False,
        )

    def _build_snapshot(self, symbol: str, bars: list, tick: dict, open_positions: dict) -> CoreAShadowSnapshot:
        self._trace_id_counter += 1
        trace_id = f"core_a_{int(time.time() * 1000)}_{self._trace_id_counter}"
        timestamp = datetime.now().isoformat()
        price = tick.get("price", 0.0)
        volume = tick.get("volume", 0)
        bid_vol = tick.get("bid_vol", 0)
        ask_vol = tick.get("ask_vol", 0)
        daily_pnl = 0.0
        daily_trades = 0
        if open_positions:
            for _sym, pos in open_positions.items():
                if isinstance(pos, dict):
                    dp = pos.get("entry", 0.0)
                    if isinstance(dp, (int, float)):
                        daily_pnl += dp
        input_summary = {
            "symbol": symbol,
            "price": price,
            "volume": volume,
            "bid_vol": bid_vol,
            "ask_vol": ask_vol,
            "open_positions_count": len(open_positions) if open_positions else 0,
        }
        vetoes: list[dict] = []
        reasons: list[str] = []
        warnings: list[str] = []
        veto_summary: dict | None = None
        market_reality_summary: dict | None = None
        sizing_summary: dict | None = None
        microstructure_summary: dict | None = None
        event_summary: dict | None = None
        confidence_summary: dict | None = None
        precheck_summary: dict | None = None

        if self._layer is not None and price > 0:
            try:
                ref_price = bars[-1]["close"] if bars else price
                valid, reason = self._layer.validate_price_limit(price, ref_price)
                cost_data = self._layer.calculate_costs(price, max(volume, 1000))
                slippage_est = self._layer.estimate_slippage(price, max(volume, 1000))
                fill_rate = self._layer.estimate_fill_rate(max(volume, 1000))
                market_reality_summary = {
                    "price_limit_valid": valid,
                    "price_limit_reason": reason,
                    "costs": cost_data,
                    "slippage_estimate": slippage_est,
                    "fill_rate": fill_rate,
                }
                if not valid:
                    vetoes.append({"source": "R028", "reason": reason})
                    reasons.append(f"R028: {reason}")
            except Exception as exc:
                warnings.append(f"R028 evaluation error: {exc}")
                market_reality_summary = {"error": str(exc)}

        if self._cost is not None and price > 0:
            try:
                expected_costs = self._cost.calculate_expected_costs(price, max(volume, 1000))
                if market_reality_summary is None:
                    market_reality_summary = {}
                market_reality_summary["expected_costs"] = expected_costs
                reasons.append(f"R029 cost: {expected_costs.get('total_cost', 0):.2f}")
            except Exception as exc:
                warnings.append(f"R029 cost error: {exc}")

        if self._slippage_mon is not None and price > 0:
            try:
                expected_slippage = self._slippage_mon.estimate_expected_slippage(price, max(volume, 1000))
                if market_reality_summary is None:
                    market_reality_summary = {}
                market_reality_summary["expected_slippage"] = expected_slippage
                reasons.append(f"R029 slippage: {expected_slippage.get('expected_slippage', 0):.4f}")
            except Exception as exc:
                warnings.append(f"R029 slippage error: {exc}")

        if self._fill is not None:
            try:
                fill_result = self._fill.estimate_fill_probability(max(volume, 1000))
                if market_reality_summary is None:
                    market_reality_summary = {}
                market_reality_summary["fill_probability"] = fill_result
                reasons.append(f"R029 fill: {fill_result.get('fill_probability', 0):.2%}")
            except Exception as exc:
                warnings.append(f"R029 fill error: {exc}")

        if self._integration is not None and price > 0:
            try:
                ref_price = bars[-1]["close"] if bars else price
                intg_result = self._integration.evaluate_order_with_tracking(price, max(volume, 1000), ref_price)
                if not intg_result.get("passed", True):
                    for r in intg_result.get("reasons", []):
                        vetoes.append({"source": "R029_INTG", "reason": r})
                        reasons.append(f"R029 integration: {r}")
            except Exception as exc:
                warnings.append(f"R029 integration error: {exc}")

        if _TradeCandidate is not None and _DecisionPreCheckList is not None and self._precheck is not None and price > 0:
            try:
                candidate = _TradeCandidate(
                    symbol=symbol,
                    side="long",
                    quantity=max(volume, 1000),
                    price=price,
                    signal_source="shadow",
                    confidence_raw=50.0,
                    strategy="core_a1_shadow",
                )
                result = self._precheck.check(candidate)
                if result is not None:
                    precheck_summary = {
                        "passed": getattr(result, "passed", False),
                        "veto": getattr(result, "veto", None),
                        "veto_reason_code": getattr(result, "veto_reason_code", None),
                        "vetoes": getattr(result, "vetoes", []),
                    }
                    if hasattr(result, "veto") and result.veto:
                        vetoes.append({"source": "R030", "reason": result.veto})
                        reasons.append(f"R030 precheck: {result.veto}")
            except Exception as exc:
                warnings.append(f"R030 precheck error: {exc}")
                precheck_summary = {"error": str(exc)}

        if self._confidence is not None:
            try:
                decomp = self._confidence.decompose(confidence_raw=50.0, source_scores=None)
                if decomp is not None:
                    confidence_summary = {
                        "raw_confidence": getattr(decomp, "raw_confidence", 50.0),
                        "overall_calibrated": getattr(decomp, "overall_calibrated", 50.0),
                        "veto_reason": getattr(decomp, "veto_reason", None),
                    }
            except Exception as exc:
                warnings.append(f"R031 confidence error: {exc}")

        if self._sizing is not None:
            try:
                sizing_result = self._sizing.check(quantity=max(volume, 1000), price=price)
                if sizing_result is not None:
                    sizing_summary = {
                        "passed": getattr(sizing_result, "passed", False),
                        "reason": getattr(sizing_result, "reason", ""),
                        "recommended_qty": getattr(sizing_result, "recommended_qty", 0),
                    }
                    if hasattr(sizing_result, "veto_reason") and sizing_result.veto_reason:
                        vetoes.append({"source": "R047", "reason": sizing_result.veto_reason})
                        reasons.append(f"R047 sizing: {sizing_result.veto_reason}")
            except Exception as exc:
                warnings.append(f"R047 sizing error: {exc}")

        if self._micro is not None:
            try:
                feat = self._micro.compute_features([])
                microstructure_summary = {
                    "features_available": feat is not None,
                }
            except Exception as exc:
                warnings.append(f"R048 microstructure error: {exc}")

        if self._news is not None:
            event_summary = {"news_analyzer_available": True, "events_analyzed": 0}
        if self._dedup is not None and event_summary is not None:
            event_summary["deduplicator_available"] = True
        if self._scorer is not None and event_summary is not None:
            event_summary["importance_scorer_available"] = True
        if self._conflict is not None and event_summary is not None:
            event_summary["conflict_integrator_available"] = True

        shadow_result = "unavailable" if not any([self._layer, self._cost, self._precheck, self._sizing]) else "available"

        return CoreAShadowSnapshot(
            trace_id=trace_id,
            timestamp=timestamp,
            symbol=symbol,
            input_summary=input_summary,
            precheck_summary=precheck_summary,
            veto_summary=veto_summary or ({"vetoes": vetoes} if vetoes else None),
            market_reality_summary=market_reality_summary,
            sizing_summary=sizing_summary,
            microstructure_summary=microstructure_summary,
            event_summary=event_summary,
            confidence_summary=confidence_summary,
            shadow_result=shadow_result,
            vetoes=vetoes,
            reasons=reasons,
            warnings=warnings,
            source_versions=_SOURCE_VERSIONS,
            no_order_side_effects=True,
            order_execution_allowed=False,
        )
