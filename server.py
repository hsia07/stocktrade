"""
TW AI Trading Dashboard
FastAPI + WebSocket + Shioaji

Run:
  pip install -r requirements.txt
  python server.py
"""

import asyncio, json, logging, os, time, math
from datetime import datetime, date, timedelta
from collections import deque
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Optional
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# R007 Silence Protection imports
from monitoring.silence.detector import SilenceDetector
from monitoring.silence.recovery import SilenceRecovery, SilenceReport
# R011 Artifact Management import
from automation.control.artifacts.r011_artifact_management import ArtifactManager
# R006 Health Circuit Integration imports
from health.monitor import HealthMonitor
from circuit.breaker import CircuitBreaker
from failover.center import DegradationCenter, DegradationStrategy
# R008 Mode Control Integration imports
from governance.state_machine.mode_controller import ModeController, Mode
from governance.state_machine.mode_recorder import ModeRecorder

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("TW-AI-TRADER")

# ══════════════════════════════════════════════
# 設定
# ══════════════════════════════════════════════
PAPER_TRADE   = os.getenv("PAPER_TRADE", "true").lower() == "true"
AUTO_TRADE    = os.getenv("AUTO_TRADE", "true").lower() == "true"
TOTAL_CAPITAL = float(os.getenv("TOTAL_CAPITAL", "500000"))
WATCH_LIST    = os.getenv("WATCH_LIST", "2330,2454,2382,3017,2317,2308").split(",")

# ══════════════════════════════════════════════
# 資料模型
# ══════════════════════════════════════════════
class Direction(str, Enum):
    LONG  = "long"
    SHORT = "short"
    NONE  = "none"

@dataclass
class Signal:
    symbol: str
    direction: Direction
    entry_price: float
    stop_loss: float
    target_1: float
    target_2: float
    confidence: float
    reason: str
    timestamp: str

@dataclass
class AgentReport:
    role: str
    icon: str
    status: str          # ok | warn | alert | idle
    summary: str
    details: list        # list of str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%H:%M:%S")

OBSERVER_SCHEMA_VERSION = "1.0"

class ObservableEvent:
    OBSERVER_SCHEMA_VERSION = OBSERVER_SCHEMA_VERSION
    VALID_STATUSES = {"ok", "warn", "alert", "idle", "info", "error", "success", "pending"}
    VALID_EVENT_TYPES = {"trade", "signal", "risk", "market", "system", "recovery", "error", "audit"}
    
    def __init__(self):
        self.events = []
        self._schema = {
            "version": self.OBSERVER_SCHEMA_VERSION,
            "required_fields": ["event_id", "timestamp", "event_type", "source", "status", "message", "details"]
        }

    def emit(self, event_type: str, source: str, status: str, message: str, details: dict = None) -> dict:
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {self.VALID_STATUSES}")
        if event_type not in self.VALID_EVENT_TYPES:
            raise ValueError(f"Invalid event_type: {event_type}. Must be one of {self.VALID_EVENT_TYPES}")
        
        event = {
            "event_id": f"{event_type}_{int(time.time() * 1000)}",
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "source": source,
            "status": status,
            "message": message,
            "details": details or {},
            "schema_version": self.OBSERVER_SCHEMA_VERSION
        }
        self.events.append(event)
        return event

    def emit_trade(self, symbol: str, action: str, price: float, lots: int, pnl: float = None) -> dict:
        details = {"symbol": symbol, "action": action, "price": price, "lots": lots}
        if pnl is not None:
            details["pnl"] = pnl
        return self.emit("trade", f"execution_{symbol}", "success", f"{action} {symbol}", details)

    def emit_signal(self, symbol: str, direction: str, confidence: float, reason: str) -> dict:
        details = {"symbol": symbol, "direction": direction, "confidence": confidence, "reason": reason}
        return self.emit("signal", f"signal_{symbol}", "info", f"{direction} signal", details)

    def emit_risk_alert(self, symbol: str, alert_type: str, details: dict) -> dict:
        return self.emit("risk", f"risk_{symbol}", "alert", alert_type, details)

    def emit_error(self, source: str, error_type: str, message: str, details: dict = None) -> dict:
        return self.emit("error", source, "error", message, details or {"error_type": error_type})

    def emit_recovery(self, source: str, recovery_type: str, details: dict = None) -> dict:
        return self.emit("recovery", source, "success", f"Recovery: {recovery_type}", details)

    def emit_audit(self, action: str, actor: str, details: dict = None) -> dict:
        return self.emit("audit", "audit_system", "info", f"Audit: {action}", details or {"actor": actor})

    def get_events(self, event_type: str = None, source: str = None, status: str = None) -> list:
        filtered = self.events
        if event_type:
            filtered = [e for e in filtered if e.get("event_type") == event_type]
        if source:
            filtered = [e for e in filtered if e.get("source") == source]
        if status:
            filtered = [e for e in filtered if e.get("status") == status]
        return filtered

    def validate_schema(self) -> dict:
        valid = True
        for event in self.events:
            for field in self._schema["required_fields"]:
                if field not in event:
                    valid = False
                    break
        return {"valid": valid, "schema": self._schema, "event_count": len(self.events)}

class DataPathSeparator:
    def __init__(self):
        self._realtime_cache = {}
        self._history_cache = {}
        self._query_count = {"realtime": 0, "history": 0}

    def get_realtime_data(self, symbol: str, bars: list) -> dict:
        if symbol in self._realtime_cache:
            return self._realtime_cache[symbol]
        data = {
            "close": bars[-1]["close"] if bars else 0,
            "volume": bars[-1]["volume"] if bars else 0,
            "bid_vol": 0,
            "ask_vol": 0,
        }
        self._realtime_cache[symbol] = data
        self._query_count["realtime"] += 1
        return data

    def get_history_data(self, symbol: str, bars: list, lookback: int = 20) -> list:
        cache_key = f"{symbol}_{lookback}"
        if cache_key in self._history_cache:
            return self._history_cache[cache_key]
        data = bars[-lookback:] if len(bars) >= lookback else bars
        self._history_cache[cache_key] = data
        self._query_count["history"] += 1
        return data

    def clear_history_cache(self):
        self._history_cache.clear()

    def get_stats(self) -> dict:
        return {
            "realtime_queries": self._query_count["realtime"],
            "history_queries": self._query_count["history"],
            "realtime_cache_size": len(self._realtime_cache),
            "history_cache_size": len(self._history_cache),
        }

class MultiLayerCache:
    L1_TTL_MS = 1000
    L2_TTL_MS = 30000
    
    def __init__(self):
        self._l1_cache = {}
        self._l2_cache = {}
        self._l1_timestamps = {}
        self._l2_timestamps = {}
        self._source_priority = ["live", "mock", "historical"]
        self._cache_stats = {"l1_hit": 0, "l1_miss": 0, "l2_hit": 0, "l2_miss": 0, "source_fallback": 0}

    def _make_key(self, category: str, symbol: str, source: str = "live") -> str:
        return f"{category}:{source}:{symbol}"

    def _is_expired(self, timestamp: float, ttl_ms: int) -> bool:
        import time
        return (time.time() * 1000) - timestamp > ttl_ms

    def get(self, category: str, symbol: str, source: str = "live", allow_fallback: bool = True) -> tuple:
        cache_key = self._make_key(category, symbol, source)
        
        if cache_key in self._l1_cache:
            if not self._is_expired(self._l1_timestamps[cache_key], self.L1_TTL_MS):
                self._cache_stats["l1_hit"] += 1
                return self._l1_cache[cache_key], "l1", "hit"
            else:
                del self._l1_cache[cache_key]
                del self._l1_timestamps[cache_key]
        
        self._cache_stats["l1_miss"] += 1
        
        if cache_key in self._l2_cache:
            if not self._is_expired(self._l2_timestamps[cache_key], self.L2_TTL_MS):
                self._cache_stats["l2_hit"] += 1
                self._l1_cache[cache_key] = self._l2_cache[cache_key]
                import time
                self._l1_timestamps[cache_key] = time.time() * 1000
                return self._l2_cache[cache_key], "l2", "hit"
            else:
                del self._l2_cache[cache_key]
                del self._l2_timestamps[cache_key]
        
        self._cache_stats["l2_miss"] += 1
        
        if allow_fallback:
            for fallback_source in self._source_priority:
                if fallback_source == source:
                    continue
                fallback_key = self._make_key(category, symbol, fallback_source)
                if fallback_key in self._l2_cache:
                    import time
                    if not self._is_expired(self._l2_timestamps[fallback_key], self.L2_TTL_MS):
                        self._cache_stats["source_fallback"] += 1
                        return self._l2_cache[fallback_key], "fallback", fallback_source
        
        return None, "miss", None

    def set(self, category: str, symbol: str, data: any, source: str = "live"):
        import time
        cache_key = self._make_key(category, symbol, source)
        timestamp = time.time() * 1000
        
        self._l1_cache[cache_key] = data
        self._l1_timestamps[cache_key] = timestamp
        self._l2_cache[cache_key] = data
        self._l2_timestamps[cache_key] = timestamp

    def invalidate(self, category: str, symbol: str, source: str = None):
        if source:
            cache_key = self._make_key(category, symbol, source)
            self._l1_cache.pop(cache_key, None)
            self._l1_timestamps.pop(cache_key, None)
            self._l2_cache.pop(cache_key, None)
            self._l2_timestamps.pop(cache_key, None)
        else:
            for src in self._source_priority:
                cache_key = self._make_key(category, symbol, src)
                self._l1_cache.pop(cache_key, None)
                self._l1_timestamps.pop(cache_key, None)
                self._l2_cache.pop(cache_key, None)
                self._l2_timestamps.pop(cache_key, None)

    def clear_all(self):
        self._l1_cache.clear()
        self._l2_cache.clear()
        self._l1_timestamps.clear()
        self._l2_timestamps.clear()

    def get_stats(self) -> dict:
        return {
            "l1_hit": self._cache_stats["l1_hit"],
            "l1_miss": self._cache_stats["l1_miss"],
            "l2_hit": self._cache_stats["l2_hit"],
            "l2_miss": self._cache_stats["l2_miss"],
            "source_fallback": self._cache_stats["source_fallback"],
            "l1_size": len(self._l1_cache),
            "l2_size": len(self._l2_cache)
        }

    def get_realtime_data(self, symbol: str, bars: list) -> dict:
        if symbol in self._realtime_cache:
            return self._realtime_cache[symbol]
        data = {
            "close": bars[-1]["close"] if bars else 0,
            "volume": bars[-1]["volume"] if bars else 0,
            "bid_vol": 0,
            "ask_vol": 0,
        }
        self._realtime_cache[symbol] = data
        self._query_count["realtime"] += 1
        return data

    def get_history_data(self, symbol: str, bars: list, lookback: int = 20) -> list:
        cache_key = f"{symbol}_{lookback}"
        if cache_key in self._history_cache:
            return self._history_cache[cache_key]
        data = bars[-lookback:] if len(bars) >= lookback else bars
        self._history_cache[cache_key] = data
        self._query_count["history"] += 1
        return data

@dataclass
class TradeRecord:
    id: str
    symbol: str
    direction: str
    entry: float
    exit: float
    lots: int
    pnl: float
    reason: str
    open_time: str
    close_time: str

class DecisionLatencyBudget:
    DISPLAY_ONLY_MS = 2000
    TRADING_DECISION_MS = 5000
    UNACCEPTABLE_MS = 10000
    
    def __init__(self):
        self._decision_times = {}
        self._degrade_count = 0
        self._fallback_mode = False
        self._last_fallback_reason = ""

    def check_latency(self, component: str, latency_ms: float) -> dict:
        if latency_ms > self.UNACCEPTABLE_MS:
            self._degrade_count += 1
            self._fallback_mode = True
            self._last_fallback_reason = f"{component} exceeded {self.UNACCEPTABLE_MS}ms"
            return {
                "status": "degraded",
                "mode": "fallback",
                "latency_ms": latency_ms,
                "reason": self._last_fallback_reason,
                "can_trade": False,
                "output_format": "fallback"
            }
        elif latency_ms > self.TRADING_DECISION_MS:
            return {
                "status": "warning",
                "mode": "display_only",
                "latency_ms": latency_ms,
                "can_trade": False,
                "output_format": "display"
            }
        elif latency_ms > self.DISPLAY_ONLY_MS:
            return {
                "status": "ok",
                "mode": "full",
                "latency_ms": latency_ms,
                "can_trade": True,
                "output_format": "full"
            }
        else:
            return {
                "status": "ok",
                "mode": "full",
                "latency_ms": latency_ms,
                "can_trade": True,
                "output_format": "full"
            }

    def check_ai_timeout(self, component: str, timeout_ms: float) -> dict:
        if timeout_ms > self.TRADING_DECISION_MS:
            self._degrade_count += 1
            self._fallback_mode = True
            self._last_fallback_reason = f"AI {component} timeout"
            return {
                "status": "degraded",
                "mode": "fallback",
                "timeout_ms": timeout_ms,
                "reason": self._last_fallback_reason,
                "can_trade": False,
                "output_format": "fallback",
                "explanation": "AI timeout - revert to last known safe state"
            }
        return {
            "status": "ok",
            "mode": "full",
            "timeout_ms": timeout_ms,
            "can_trade": True,
            "output_format": "full"
        }

    def recover_from_fallback(self) -> bool:
        if self._fallback_mode and self._degrade_count < 3:
            self._fallback_mode = False
            self._last_fallback_reason = ""
            return True
        return False

    def get_status(self) -> dict:
        return {
            "degrade_count": self._degrade_count,
            "fallback_mode": self._fallback_mode,
            "last_fallback_reason": self._last_fallback_reason,
            "can_trade": not self._fallback_mode
        }

# ══════════════════════════════════════════════
# 角色一：量化研究員 (Quant Researcher)
# 職責：發現 alpha、設計策略邏輯
# ══════════════════════════════════════════════
class QuantResearcher:
    def __init__(self):
        self.alpha_signals = {}
        self._cache = {}

    def _fast_ma(self, data: list, period: int) -> float:
        if len(data) < period:
            return 0.0
        return sum(data[-period:]) / period

    def _fast_std(self, data: list, period: int, mean: float) -> float:
        if len(data) < period:
            return 0.0
        variance = sum((x - mean) ** 2 for x in data[-period:]) / period
        return variance ** 0.5

    def analyze(self, symbol: str, bars: list) -> AgentReport:
        if len(bars) < 20:
            return AgentReport("Quant Researcher", "QR", "idle", "Waiting for more bars", ["Need at least 20 bars"])

        closes  = [b["close"] for b in bars]
        volumes = [b["volume"] for b in bars]
        highs   = [b["high"] for b in bars]

        price_chg = (closes[-1] - closes[-5]) / closes[-5] * 100
        vol_base = sum(volumes[-6:-1]) / 5
        vol_chg = (volumes[-1] - vol_base) / (vol_base or 1) * 100
        vol_price_diverge = vol_chg > 50 and price_chg < 0

        ma20 = sum(closes[-20:]) / 20
        std20 = (sum((c - ma20) ** 2 for c in closes[-20:]) / 20) ** 0.5
        bb_width = (std20 * 2) / ma20 * 100 if ma20 else 0
        squeeze = bb_width < 3.5

        highest_20 = max(highs[-21:-1])
        breakout = closes[-1] > highest_20

        ema5_now = sum(closes[-5:]) / 5
        ema5_prev = sum(closes[-8:-3]) / 5
        slope = (ema5_now - ema5_prev) / ema5_prev * 100 if ema5_prev else 0

        alpha_score = 0
        findings = []
        if breakout:
            alpha_score += 30
            findings.append(f"Breakout above 20-bar high: {closes[-1]:.2f} > {highest_20:.2f}")
        if squeeze:
            alpha_score += 25
            findings.append(f"Bollinger squeeze width {bb_width:.1f}%")
        if slope > 0.3:
            alpha_score += 20
            findings.append(f"Short EMA slope rising +{slope:.2f}%")
        if vol_price_diverge:
            alpha_score -= 20
            findings.append(f"Volume/price divergence: volume {vol_chg:.0f}% vs price {price_chg:.1f}%")
        if not findings:
            findings.append("No clear alpha feature detected")

        self.alpha_signals[symbol] = alpha_score
        status = "ok" if alpha_score >= 40 else "warn" if alpha_score >= 10 else "idle"
        return AgentReport("Quant Researcher", "QR", status, f"{symbol} alpha score {alpha_score}/75", findings)

class Backtester:
    def __init__(self):
        self.results = {}
        self._cache = {}

    def _compute_emas(self, closes: list) -> tuple:
        if len(closes) < 21:
            return []
        ema5_arr = []
        ema20_arr = []
        for i in range(20, len(closes)):
            window = closes[:i+1]
            ema5_arr.append(sum(window[-5:]) / 5)
            ema20_arr.append(sum(window[-20:]) / 20)
        return ema5_arr, ema20_arr

    def run(self, symbol: str, bars: list) -> AgentReport:
        if len(bars) < 30:
            return AgentReport("Backtester", "BT", "idle", "Need more history for backtest", ["Need at least 30 bars"])

        closes = [b["close"] for b in bars]
        ema5_arr, ema20_arr = self._compute_emas(closes)
        
        trades = []
        in_trade = None
        for i, (ema5, ema20) in enumerate(zip(ema5_arr, ema20_arr)):
            actual_idx = i + 20
            if in_trade is None and ema5 > ema20 * 1.002:
                in_trade = {"entry": closes[actual_idx], "idx": actual_idx}
            elif in_trade and (ema5 < ema20 or actual_idx - in_trade["idx"] >= 30):
                pnl = closes[actual_idx] - in_trade["entry"]
                trades.append(pnl)
                in_trade = None

        if in_trade is not None:
            trades.append(closes[-1] - in_trade["entry"])

        if not trades:
            return AgentReport("Backtester", "BT", "idle", "No completed trades", ["Strategy has not triggered yet"])

        wins    = [p for p in trades if p > 0]
        losses  = [p for p in trades if p < 0]
        wr      = len(wins) / len(trades) * 100
        avg_w   = sum(wins) / len(wins) if wins else 0
        avg_l   = sum(losses) / len(losses) if losses else -1
        pf      = abs(sum(wins) / sum(losses)) if losses else 99
        cum     = []
        running = 0
        for p in trades:
            running += p
            cum.append(running)
        max_dd = min(c - max(cum[: i + 1]) for i, c in enumerate(cum)) if cum else 0

        self.results[symbol] = {"win_rate": wr, "profit_factor": pf}
        status = "ok" if wr > 55 and pf > 1.5 else "warn"
        return AgentReport(
            "Backtester",
            "BT",
            status,
            f"{symbol} {len(trades)} trades, win rate {wr:.0f}%",
            [
                f"Win rate: {wr:.1f}%",
                f"Profit factor: {pf:.2f}",
                f"Avg win/loss: {avg_w:.2f} / {avg_l:.2f}",
                f"Max drawdown: {max_dd:.2f}",
                f"Net result: {sum(trades):+.2f}",
            ],
        )

class RiskOfficer:
    def __init__(self):
        self.daily_pnl         = 0.0
        self.daily_trades      = 0
        self.consecutive_loss  = 0
        self.open_positions    = {}
        self.is_halted         = False
        self.halt_reason       = ""
        self.last_reset_date   = date.today()
        # Risk thresholds
        self.MAX_DAILY_LOSS    = float(os.getenv("MAX_DAILY_LOSS", "5000"))
        self.MAX_SINGLE_LOSS   = float(os.getenv("MAX_SINGLE_LOSS", "1500"))
        self.MAX_TRADES        = int(os.getenv("MAX_TRADES", "6"))
        self.MAX_POSITIONS     = int(os.getenv("MAX_POSITIONS", "2"))
        self.MAX_CONSEC_LOSS   = int(os.getenv("MAX_CONSEC_LOSS", "3"))
        self.MIN_CONFIDENCE    = float(os.getenv("MIN_CONFIDENCE", "65"))
        self.TRADE_START       = os.getenv("TRADE_START", "09:10")
        self.TRADE_END         = os.getenv("TRADE_END", "13:00")
        self.FORCE_CLOSE_TIME  = os.getenv("FORCE_CLOSE", os.getenv("FORCE_CLOSE_TIME", "13:20"))
        self.MAX_CHASE_PCT     = float(os.getenv("MAX_CHASE_PCT", "0.005"))

    def ensure_session(self):
        today = date.today()
        if today != self.last_reset_date:
            self.reset_daily(today)

    def reset_daily(self, reset_date: Optional[date] = None):
        self.daily_pnl, self.daily_trades = 0.0, 0
        self.consecutive_loss = 0
        self.open_positions   = {}
        self.is_halted        = False
        self.halt_reason      = ""
        self.last_reset_date  = reset_date or date.today()

    def can_enter(self, signal: Signal, current_price: float) -> tuple[bool, str]:
        self.ensure_session()
        now_str = datetime.now().strftime("%H:%M")
        chase_pct = abs(current_price - signal.entry_price) / signal.entry_price if signal.entry_price else 0.0
        checks = [
            (not self.is_halted,                             f"Trading halted: {self.halt_reason}"),
            (self.TRADE_START <= now_str <= self.TRADE_END, f"Outside trading window {self.TRADE_START}-{self.TRADE_END}"),
            (self.daily_trades < self.MAX_TRADES,           f"Daily trade limit reached: {self.MAX_TRADES}"),
            (self.daily_pnl > -self.MAX_DAILY_LOSS,         f"Daily loss limit reached: {-self.MAX_DAILY_LOSS:.0f}"),
            (len(self.open_positions) < self.MAX_POSITIONS, f"Max open positions reached: {self.MAX_POSITIONS}"),
            (signal.symbol not in self.open_positions,      f"{signal.symbol} already has an open position"),
            (signal.confidence >= self.MIN_CONFIDENCE,      f"Confidence too low: {signal.confidence:.0f} < {self.MIN_CONFIDENCE:.0f}"),
            (self.consecutive_loss < self.MAX_CONSEC_LOSS,  f"Consecutive loss limit reached: {self.consecutive_loss}"),
            (chase_pct < self.MAX_CHASE_PCT,                f"Chase price too far: {chase_pct:.3%} >= {self.MAX_CHASE_PCT:.3%}"),
        ]
        for ok, reason in checks:
            if not ok:
                return False, reason
        return True, "OK"

    def calc_lots(self, signal: Signal, price: float) -> int:
        risk_per_share = abs(price - signal.stop_loss)
        if risk_per_share <= 0:
            return 0
        max_by_loss     = int(self.MAX_SINGLE_LOSS / risk_per_share)
        max_by_capital  = int(TOTAL_CAPITAL * 0.25 / (price * 1000))
        return max(min(max_by_loss, max_by_capital, 3), 0)

    def on_entry(self, signal: Signal, lots: int, price: float):
        self.ensure_session()
        self.daily_trades += 1
        self.open_positions[signal.symbol] = {
            "direction": signal.direction,
            "entry": price,
            "entry_time": signal.timestamp,
            "lots": lots,
            "stop": signal.stop_loss,
            "t1": signal.target_1,
            "t2": signal.target_2,
            "partial": False,
            "realized_pnl": 0.0,
        }

    def on_partial_exit(self, symbol: str, pnl: float):
        self.ensure_session()
        self.daily_pnl += pnl

    def on_exit(self, symbol: str, pnl: float):
        self.ensure_session()
        self.daily_pnl += pnl
        self.open_positions.pop(symbol, None)
        if pnl < 0:
            self.consecutive_loss += 1
            if self.consecutive_loss >= self.MAX_CONSEC_LOSS:
                self.is_halted   = True
                self.halt_reason = f"Hit {self.consecutive_loss} consecutive losing trades"
        else:
            self.consecutive_loss = 0

    def get_report(self) -> AgentReport:
        self.ensure_session()
        remain_loss   = self.MAX_DAILY_LOSS + self.daily_pnl
        remain_trades = self.MAX_TRADES - self.daily_trades
        status = "alert" if self.is_halted else "warn" if remain_loss < self.MAX_DAILY_LOSS * 0.3 else "ok"
        details = [
            f"Daily PnL: {self.daily_pnl:+.0f} NT$",
            f"Remaining loss budget: {remain_loss:.0f} NT$",
            f"Remaining trade count: {remain_trades}",
            f"Open positions: {len(self.open_positions)} / {self.MAX_POSITIONS}",
            f"Consecutive losses: {self.consecutive_loss} / {self.MAX_CONSEC_LOSS}",
            f"Trading status: {'HALTED - ' + self.halt_reason if self.is_halted else 'Active'}",
        ]
        return AgentReport("Risk Officer", "RO", status, f"Loss budget left {remain_loss:.0f}", details)

class SignalEngineer:
    def __init__(self):
        self._vwap = {}   # symbol -> {cum_pv, cum_vol}
        self._last_bar_time = {}

    def reset_vwap(self, symbol: str):
        self._vwap[symbol] = {"cum_pv": 0.0, "cum_vol": 0}
        self._last_bar_time[symbol] = None

    def update_vwap(self, symbol: str, bar: dict):
        bar_time = bar.get("time")
        if symbol not in self._vwap:
            self.reset_vwap(symbol)
        if bar_time and self._last_bar_time.get(symbol) == bar_time:
            return
        mid = (bar["high"] + bar["low"] + bar["close"]) / 3
        self._vwap[symbol]["cum_pv"]  += mid * bar["volume"]
        self._vwap[symbol]["cum_vol"] += bar["volume"]
        self._last_bar_time[symbol] = bar_time

    def vwap(self, symbol: str) -> float:
        d = self._vwap.get(symbol, {})
        if not d or d["cum_vol"] == 0:
            return 0
        return d["cum_pv"] / d["cum_vol"]

    def _ema(self, closes: list, span: int) -> float:
        k = 2 / (span + 1)
        e = closes[0]
        for c in closes[1:]:
            e = c * k + e * (1 - k)
        return e

    def _rsi(self, closes: list, period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains  = [max(d, 0) for d in deltas[-period:]]
        losses = [-min(d, 0) for d in deltas[-period:]]
        ag, al = sum(gains) / period, sum(losses) / period
        if al == 0:
            return 100
        return 100 - 100 / (1 + ag / al)

    def _atr(self, bars: list, period: int = 14) -> float:
        trs = []
        for i in range(1, len(bars)):
            h, l, pc = bars[i]["high"], bars[i]["low"], bars[i - 1]["close"]
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        return sum(trs[-period:]) / min(len(trs), period) if trs else 1

    def evaluate(self, symbol: str, bars: list, tick: dict, order_book: dict) -> tuple[Optional[Signal], AgentReport]:
        if len(bars) < 20:
            return None, AgentReport("Signal Engineer", "SE", "idle", "Waiting for more bars", ["Need at least 20 bars"])

        closes  = [b["close"] for b in bars]
        price   = tick.get("price", closes[-1])
        vwap    = self.vwap(symbol)
        ema5    = self._ema(closes[-10:], 5)
        ema20   = self._ema(closes[-25:], 20)
        rsi     = self._rsi(closes)
        atr     = self._atr(bars)
        vol_now = bars[-1]["volume"]
        vol_avg = sum(b["volume"] for b in bars[-6:-1]) / 5
        vol_r   = vol_now / (vol_avg + 1)
        bid_v   = order_book.get("bid_vol", 100)
        ask_v   = order_book.get("ask_vol", 100)

        long_checks = {
            "price_above_vwap": price > vwap if vwap else False,
            "ema_bullish": ema5 > ema20,
            "rsi_zone": 45 <= rsi <= 70,
            "volume_confirm": vol_r >= 1.5,
            "bid_dominant": bid_v > ask_v * 1.4,
        }
        short_checks = {
            "price_below_vwap": price < vwap if vwap else False,
            "ema_bearish": ema5 < ema20,
            "rsi_zone": 30 <= rsi <= 55,
            "volume_confirm": vol_r >= 1.5,
            "ask_dominant": ask_v > bid_v * 1.4,
        }
        ls, ss = sum(long_checks.values()), sum(short_checks.values())

        bonus = (10 if vol_r > 2.5 else 0) + (8 if rsi > 65 and ls == 5 else 0) + (8 if rsi < 35 and ss == 5 else 0)
        signal = None

        indicator_lines = [
            f"VWAP: {vwap:.2f} | Price: {price:.2f}",
            f"EMA5: {ema5:.2f} EMA20: {ema20:.2f}",
            f"RSI: {rsi:.1f} | ATR: {atr:.2f}",
            f"Volume ratio: {vol_r:.2f}x | Bid/Ask vol: {bid_v}/{ask_v}",
            f"Long checks: {ls}/5 | Short checks: {ss}/5",
        ]

        if ls == 5:
            conf = min(60 + bonus, 95)
            signal = Signal(
                symbol,
                Direction.LONG,
                price,
                round(price - atr * 1.2, 2),
                round(price + atr * 1.5, 2),
                round(price + atr * 2.8, 2),
                conf,
                "Long setup confirmed",
                datetime.now().strftime("%H:%M:%S"),
            )
            indicator_lines.append(f"LONG signal {conf:.0f}% | stop {signal.stop_loss} | targets {signal.target_1}/{signal.target_2}")
            rep = AgentReport("Signal Engineer", "SE", "ok", f"LONG {symbol} confidence {conf:.0f}%", indicator_lines)
        elif ss == 5:
            conf = min(60 + bonus, 95)
            signal = Signal(
                symbol,
                Direction.SHORT,
                price,
                round(price + atr * 1.2, 2),
                round(price - atr * 1.5, 2),
                round(price - atr * 2.8, 2),
                conf,
                "Short setup confirmed",
                datetime.now().strftime("%H:%M:%S"),
            )
            indicator_lines.append(f"SHORT signal {conf:.0f}% | stop {signal.stop_loss} | targets {signal.target_1}/{signal.target_2}")
            rep = AgentReport("Signal Engineer", "SE", "alert", f"SHORT {symbol} confidence {conf:.0f}%", indicator_lines)
        else:
            rep = AgentReport("Signal Engineer", "SE", "idle", f"No setup for {symbol} ({ls}/5, {ss}/5)", indicator_lines)

        return signal, rep

class ExecutionEngineer:
    def __init__(self):
        self.orders     = []
        self.executions = []
        self._api       = None

    def set_api(self, api):
        self._api = api

    def place(self, symbol: str, action: str, lots: int, price: float, reason: str) -> dict:
        oid = f"{'P' if PAPER_TRADE else 'R'}-{symbol}-{int(time.time())}"
        rec = {
            "id": oid,
            "symbol": symbol,
            "action": action,
            "lots": lots,
            "price": price,
            "reason": reason,
            "status": "simulated" if PAPER_TRADE else "sent",
            "time": datetime.now().strftime("%H:%M:%S"),
        }
        self.orders.append(rec)
        tag = "[PAPER]" if PAPER_TRADE else "[LIVE]"
        log.info(f"{tag} {action} {symbol} {lots} lot(s) @ {price} | {reason}")

        if not PAPER_TRADE and self._api:
            try:
                from shioaji import constant
                contract = self._api.Contracts.Stocks[symbol]
                act = constant.Action.Buy if action == "Buy" else constant.Action.Sell
                order = self._api.Order(
                    price=price,
                    quantity=lots,
                    action=act,
                    price_type=constant.StockPriceType.LMT,
                    order_type=constant.OrderType.ROD,
                    order_lot=constant.StockOrderLot.Common,
                    account=self._api.stock_account,
                )
                trade = self._api.place_order(contract, order)
                rec["status"] = "placed"
                rec["broker_id"] = trade.order.id
            except Exception as e:
                rec["status"] = "error"
                rec["error"] = str(e)
                log.error(f"Order failed: {e}")
        return rec

    def get_report(self) -> AgentReport:
        today = [o for o in self.orders if o["time"][:5] >= "09:00"]
        errors = [o for o in today if o.get("status") == "error"]
        status = "alert" if errors else "ok" if today else "idle"
        details = [f"Orders today: {len(today)}"]
        details.extend(
            f"{'ERR' if o.get('status') == 'error' else 'OK'} {o['action']} {o['symbol']} {o['lots']} lot(s) @ {o['price']} {o['time']}"
            for o in today[-5:]
        )
        if len(details) == 1:
            details.append("No order records yet")
        return AgentReport("Execution Engineer", "EX", status, f"Orders today {len(today)}", details)

class MarketAnalyst:
    def __init__(self):
        self.anomalies = []

    def analyze(self, symbol: str, bars: list, tick: dict) -> AgentReport:
        if len(bars) < 5:
            return AgentReport("Market Analyst", "MA", "idle", "Waiting for more market data", ["Need at least 5 bars"])

        closes = [b["close"] for b in bars]
        volumes = [b["volume"] for b in bars]
        price = tick.get("price", closes[-1])
        findings = []

        bar_chg = (closes[-1] - closes[-2]) / closes[-2] * 100 if len(closes) >= 2 else 0
        if abs(bar_chg) > 2:
            findings.append(f"Large single-bar move: {bar_chg:+.1f}%")
            self.anomalies.append({"symbol": symbol, "type": "spike", "chg": bar_chg})

        avg_vol = sum(volumes[-6:-1]) / 5 if len(volumes) >= 6 else volumes[-1]
        vol_r = volumes[-1] / (avg_vol + 1)
        if vol_r > 3:
            findings.append(f"Volume expansion {vol_r:.1f}x")

        if len(closes) >= 6:
            up5 = all(bars[-i - 1]["close"] > bars[-i - 1]["open"] for i in range(5))
            down5 = all(bars[-i - 1]["close"] < bars[-i - 1]["open"] for i in range(5))
            if up5:
                findings.append("Five straight bullish candles, momentum is hot")
            elif down5:
                findings.append("Five straight bearish candles, momentum is weak")

        first_close = closes[0]
        day_chg = (price - first_close) / first_close * 100 if first_close else 0

        findings = findings or [f"Market is stable, intraday move {day_chg:+.1f}%"]
        findings.insert(0, f"Price {price:.2f} | intraday {day_chg:+.1f}%")

        status = "warn" if any(k in " ".join(findings) for k in ["Large", "Volume", "hot", "weak"]) else "ok"
        return AgentReport("Market Analyst", "MA", status, f"{symbol} intraday {day_chg:+.1f}%", findings)

class MockDataEngine:
    """用確定性偽隨機數模擬真實 Tick，供本機測試用"""
    def __init__(self):
        self.bases    = {
            "2330": 866, "2454": 1265, "2382": 267,
            "3017": 588, "2317": 154,  "2308": 342,
        }
        self.prices   = dict(self.bases)
        self.t        = 0
        self.bars: dict[str, deque] = {s: deque(maxlen=60) for s in WATCH_LIST}
        self._tick_buf: dict[str, list] = {s: [] for s in WATCH_LIST}
        self._cur_min: dict[str, str] = {}

    def _lcg(self, seed: int) -> float:
        return ((seed * 1664525 + 1013904223) & 0xFFFFFFFF) / 0xFFFFFFFF

    def tick(self) -> dict[str, dict]:
        self.t += 1
        result = {}
        for sym in WATCH_LIST:
            base  = self.prices.get(sym, 100)
            noise = (self._lcg(self.t * 7 + hash(sym) % 997) - 0.5) * 0.004
            trend = math.sin(self.t / 30) * 0.001
            price = round(base * (1 + noise + trend), 2)
            self.prices[sym] = price
            volume = int(200 + self._lcg(self.t + hash(sym)) * 800)
            bid    = round(price - 0.5, 2)
            ask    = round(price + 0.5, 2)
            bid_v  = int(50 + self._lcg(self.t * 3) * 200)
            ask_v  = int(50 + self._lcg(self.t * 5) * 200)
            result[sym] = {"price": price, "volume": volume, "bid": bid, "ask": ask, "bid_vol": bid_v, "ask_vol": ask_v}

            # 嘗試收 K 棒
            now_str = datetime.now().strftime("%H:%M")
            if self._cur_min.get(sym) and self._cur_min[sym] != now_str:
                buf = self._tick_buf[sym]
                if buf:
                    prices = [t["price"] for t in buf]
                    bar = {
                        "time": self._cur_min[sym],
                        "open": prices[0], "high": max(prices),
                        "low": min(prices), "close": prices[-1],
                        "volume": sum(t["volume"] for t in buf),
                    }
                    self.bars[sym].append(bar)
                self._tick_buf[sym] = []
            self._cur_min[sym] = now_str
            self._tick_buf[sym].append(result[sym])
        return result

# ══════════════════════════════════════════════
# 主控交易引擎
# ══════════════════════════════════════════════
class TradingEngine:
    def __init__(self):
        self.quant      = QuantResearcher()
        self.backtester = Backtester()
        self.risk       = RiskOfficer()
        self.signal_eng = SignalEngineer()
        self.execution  = ExecutionEngineer()
        self.analyst    = MarketAnalyst()
        self.mock       = MockDataEngine()
        self.data_sep   = DataPathSeparator()
        self.latency_budget = DecisionLatencyBudget()
        self.observer = ObservableEvent()
        self.cache = MultiLayerCache()
        self.trades_log: list[TradeRecord] = []
        self.latest_ticks  = {}
        self.agent_reports = {}
        self._shioaji_api  = None
        self._running      = False
        # R007 Silence Protection instances
        self.silence_detector = SilenceDetector()
        self.silence_recovery = SilenceRecovery()
        # R011 Artifact Manager instance
        self.artifact_manager = ArtifactManager(
            artifacts_dir="automation/control/artifacts/runtime",
            history_dir="automation/control/history"
        )
        # R006: Health Circuit Integration instances
        self.health_monitor = HealthMonitor()
        self.circuit_breaker = CircuitBreaker(
            max_daily_loss=float(os.getenv("MAX_DAILY_LOSS", "5000")),
            max_consecutive_losses=int(os.getenv("MAX_CONSEC_LOSS", "3")),
            max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "10"))
        )
        self.degradation_center = DegradationCenter()
        # R008: Mode Control Integration instances
        self.mode_controller = ModeController()
        self.mode_recorder = ModeRecorder()
        # Initialize R008 mode from current runtime state
        self._current_r008_mode = self._map_to_r008_mode()

    def _map_to_r008_mode(self) -> Mode:
        """Map existing PAPER_TRADE/AUTO_TRADE state to R008 Mode"""
        if PAPER_TRADE:
            return Mode.SIM
        elif not AUTO_TRADE:
            return Mode.OBSERVE
        else:
            return Mode.LIVE

    def _record_mode_transition(self, from_mode: Mode, to_mode: Mode, reason: str):
        """Record mode transition in ModeRecorder"""
        self.mode_recorder.record_transition(
            from_mode=from_mode.value,
            to_mode=to_mode.value,
            operator="TradingEngine",
            reason=reason
        )

    def _validate_mode_allows_trading(self) -> bool:
        """Check if current R008 mode allows trading"""
        current_mode = self._current_r008_mode
        # Trading allowed in SIM, SHADOW, LIVE modes
        return current_mode in (Mode.SIM, Mode.SHADOW, Mode.LIVE)

    def connect_shioaji(self):
        if PAPER_TRADE:
            log.info("Paper trading mode, skipping Shioaji login")
            return
        try:
            import shioaji as sj
            api = sj.Shioaji()
            api.login(
                api_key=os.getenv("SHIOAJI_API_KEY", ""),
                secret_key=os.getenv("SHIOAJI_SECRET_KEY", ""),
                fetch_contract=True,
            )
            api.activate_ca(
                ca_path=os.getenv("SHIOAJI_CERT_PATH", ""),
                ca_passwd=os.getenv("SHIOAJI_CERT_PASS", ""),
                person_id=os.getenv("SHIOAJI_ACCOUNT_ID", ""),
            )
            self._shioaji_api = api
            self.execution.set_api(api)
            log.info("Shioaji connected")
        except Exception as e:
            log.warning(f"Shioaji connection failed, falling back to mock data: {e}")

    async def run_loop(self):
        self._running = True
        log.info("Trading engine started")
        while self._running:
            self.risk.ensure_session()
            # R007: Update heartbeat each loop iteration
            self.silence_detector.update_heartbeat()
            # R006: Health check at loop start
            health_results = self.health_monitor.run_checks()
            self._last_health_aggregate = self.health_monitor.aggregate_status(health_results)
            health_aggregate = self._last_health_aggregate
            if health_aggregate['status'] == 'critical':
                class SimpleHealthStatus:
                    def is_healthy(self): return False
                    def has_paper_trading_enabled(self): return PAPER_TRADE
                self.degradation_center.evaluate_and_degrade(SimpleHealthStatus())
                log.warning(f"R006 Health critical: {health_aggregate['details']}")
                # R008: Record degradation -> PAUSE mode transition
                old_mode = self._current_r008_mode
                self._current_r008_mode = Mode.PAUSE
                self._record_mode_transition(old_mode, Mode.PAUSE, "R006 DegradationCenter triggered PAUSE_TRADING")
                log.info(f"R008 Mode transition: {old_mode.value} -> {Mode.PAUSE.value} (degradation)")
            elif self.degradation_center.get_current_strategy() is not None:
                self.degradation_center.restore()
                # R008: Record PAUSE -> previous mode transition
                old_mode = self._current_r008_mode
                restored_mode = self._map_to_r008_mode()
                self._current_r008_mode = restored_mode
                self._record_mode_transition(old_mode, restored_mode, "R006 DegradationCenter restored")
                log.info(f"R008 Mode transition: {old_mode.value} -> {restored_mode.value} (degradation restored)")
            ticks = self.mock.tick()
            self.latest_ticks = ticks
            # R007: Update market data timestamp
            self.silence_detector.update_market_data()

            # R006: Degradation hard gate - health critical blocks trading
            if self.degradation_center.get_current_strategy() == DegradationStrategy.PAUSE_TRADING:
                log.warning("R006 Degradation: PAUSE_TRADING active, skipping trade execution")
                await asyncio.sleep(3)
                continue

            # R006: Circuit breaker check before processing symbols
            circuit_blocked = self.circuit_breaker.should_block_trade()
            if circuit_blocked:
                log.warning(f"R006 Circuit breaker OPEN: {self.circuit_breaker.get_status()}")

            for sym in WATCH_LIST:
                tick  = ticks[sym]
                bars  = list(self.mock.bars[sym])
                bar   = bars[-1] if bars else None
                if bar:
                    self.signal_eng.update_vwap(sym, bar)

                # R007: Check silence before signal evaluation
                if self.silence_detector.is_silent():
                    silence_report = SilenceReport(
                        start_time=datetime.now() - timedelta(seconds=30),
                        duration=30
                    )
                    strategy = self.silence_recovery.evaluate_and_recover(silence_report)
                    self.observer.emit_error("silence", "recovery", f"Silence detected for {sym}, strategy: {strategy.name}")
                    log.warning(f"Silence detected for {sym}, applying recovery strategy: {strategy.name}")
                    continue

                rt_data = self.data_sep.get_realtime_data(sym, bars)

                obook = {"bid_vol": tick["bid_vol"], "ask_vol": tick["ask_vol"]}

                hist_data = self.data_sep.get_history_data(sym, bars, 20)

                self.agent_reports[f"quant_{sym}"]    = asdict(self.quant.analyze(sym, hist_data))
                self.agent_reports[f"backtest_{sym}"] = asdict(self.backtester.run(sym, hist_data))
                self.agent_reports[f"signal_{sym}"], sig = self._signal_and_report(sym, bars, tick, obook)
                self.agent_reports["risk"]             = asdict(self.risk.get_report())
                self.agent_reports["execution"]        = asdict(self.execution.get_report())
                self.agent_reports[f"market_{sym}"]    = asdict(self.analyst.analyze(sym, bars, tick))

                self.observer.emit("market", f"market_{sym}", "info", f"Updated {sym}", {"price": tick["price"]})

                latency_check = self.latency_budget.check_latency(f"signal_{sym}", 100)
                if latency_check["mode"] == "fallback":
                    self.observer.emit_error("latency", "degraded", latency_check["reason"])
                    log.warning(f"Latency degraded - fallback mode: {latency_check['reason']}")
                    sig = None
                else:
                    if sig:
                        self.observer.emit_signal(sym, str(sig.direction), sig.confidence, sig.reason)

                if sig and AUTO_TRADE:
                    # R008: Mode validation before trade execution
                    self._current_r008_mode = self._map_to_r008_mode()
                    if not self._validate_mode_allows_trading():
                        self.observer.emit_risk_alert(sym, "mode_validation", {"mode": self._current_r008_mode.value, "reason": "Current mode does not allow trading"})
                        log.warning(f"R008 Mode validation blocked {sym} signal: {self._current_r008_mode.value}")
                        continue
                    # R006: Circuit breaker check (precedence: CircuitBreaker > RiskOfficer)
                    if circuit_blocked:
                        self.observer.emit_risk_alert(sym, "circuit_breaker", {"state": "OPEN", "reason": "Circuit breaker blocking new trades"})
                        log.warning(f"R006 Circuit breaker blocked {sym} signal")
                        continue
                    ok, reason = self.risk.can_enter(sig, tick["price"])
                    if ok:
                        lots = self.risk.calc_lots(sig, tick["price"])
                        if lots > 0:
                            act = "Buy" if sig.direction == Direction.LONG else "Sell"
                            self.execution.place(sym, act, lots, tick["price"], sig.reason)
                            self.risk.on_entry(sig, lots, tick["price"])
                            self.observer.emit_trade(sym, act, tick["price"], lots)
                            # R007: Update trades timestamp on successful trade
                            self.silence_detector.update_trades()
                            # R011: Create artifact for executed trade
                            self.artifact_manager.create_artifact(
                                round_id="runtime",
                                content=f"Trade executed: {act} {sym} {lots} lots @ {tick['price']} | {sig.reason}",
                                artifact_type="trade"
                            )
                    else:
                        self.observer.emit_risk_alert(sym, "signal_blocked", {"reason": reason})
                        log.info(f"Risk blocked {sym} signal: {reason}")
                elif sig and not AUTO_TRADE:
                    log.info(f"Signal generated for {sym} but AUTO_TRADE is disabled")
                    # R011: Create artifact for signal (even if not traded)
                    self.artifact_manager.create_artifact(
                        round_id="runtime",
                        content=f"Signal: {sym} {sig.direction} conf={sig.confidence}% | {sig.reason}",
                        artifact_type="signal"
                    )

                self._manage_positions(sym, tick["price"])

            # R011: Create history entry for engine state snapshot
            try:
                self.artifact_manager.create_history_entry(
                    round_id="runtime",
                    data={
                        "daily_pnl": self.risk.daily_pnl,
                        "daily_trades": self.risk.daily_trades,
                        "is_halted": self.risk.is_halted,
                        "open_positions": list(self.risk.open_positions.keys()),
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            except Exception:
                pass

            await asyncio.sleep(3)

    def _signal_and_report(self, sym, bars, tick, obook):
        sig, rep = self.signal_eng.evaluate(sym, bars, tick, obook)
        return asdict(rep), sig

    def _manage_positions(self, symbol: str, price: float):
        pos = self.risk.open_positions.get(symbol)
        if not pos:
            return
        now_str   = datetime.now().strftime("%H:%M")
        direction = pos["direction"]
        mult      = 1 if direction == Direction.LONG else -1
        act       = "Sell" if direction == Direction.LONG else "Buy"

        def close(reason: str):
            entry = pos["entry"]
            pnl   = (price - entry) * mult * pos["lots"] * 1000 * 0.9985
            self.execution.place(symbol, act, pos["lots"], price, reason)
            self.risk.on_exit(symbol, pnl)
            # R006: Record trade result to circuit breaker
            self.circuit_breaker.record_trade_result(pnl)
            # R006: Sync circuit breaker from RiskOfficer (authoritative source for daily_pnl/consecutive_loss)
            self.circuit_breaker.sync_from_risk_officer(self.risk.daily_pnl, self.risk.consecutive_loss)
            self.trades_log.append(TradeRecord(
                id=f"T{int(time.time())}",
                symbol=symbol,
                direction=str(direction),
                entry=entry,
                exit=price,
                lots=pos["lots"],
                pnl=round(pos.get("realized_pnl", 0.0) + pnl, 0),
                reason=reason,
                open_time=pos.get("entry_time", ""),
                close_time=now_str,
            ))

        if now_str >= self.risk.FORCE_CLOSE_TIME:
            close("Force close at end of session")
            return
        if mult * (price - pos["stop"]) < 0:
            close("Stop loss hit")
            return
        if mult * (price - pos["t2"]) > 0:
            close("Final target hit")
            return
        if mult * (price - pos["t1"]) > 0 and not pos["partial"] and pos["lots"] > 1:
            half = max(1, pos["lots"] // 2)
            partial_pnl = (price - pos["entry"]) * mult * half * 1000 * 0.9985
            self.execution.place(symbol, act, half, price, "Take profit 1")
            pos["lots"] -= half
            pos["partial"] = True
            pos["realized_pnl"] = pos.get("realized_pnl", 0.0) + partial_pnl
            self.risk.on_partial_exit(symbol, partial_pnl)
            # R006: Record partial trade result to circuit breaker
            self.circuit_breaker.record_trade_result(partial_pnl)
            # R006: Sync circuit breaker from RiskOfficer (authoritative source)
            self.circuit_breaker.sync_from_risk_officer(self.risk.daily_pnl, self.risk.consecutive_loss)

    def get_state(self) -> dict:
        state = {
            "ticks":        self.latest_ticks,
            "agents":       self.agent_reports,
            "positions":    self.risk.open_positions,
            "daily_pnl":    self.risk.daily_pnl,
            "daily_trades": self.risk.daily_trades,
            "is_halted":    self.risk.is_halted,
            "trades_log":   [asdict(t) for t in self.trades_log[-20:]],
            "timestamp":    datetime.now().strftime("%H:%M:%S"),
            "mode":         "PAPER" if PAPER_TRADE else "LIVE",
            "auto_trade":  AUTO_TRADE,
        }
        # R011: Expose artifact stats to state
        try:
            state["artifact_stats"] = {
                "latest_artifact": self.artifact_manager.get_latest_artifact(),
                "total_artifacts": len(self.artifact_manager.list_artifacts()),
                "artifacts_dir": str(self.artifact_manager.artifacts_dir),
            }
        except Exception:
            state["artifact_stats"] = {"error": "artifact_manager_not_ready"}
        # R006: Expose health/circuit state to state
        try:
            state["health_status"] = getattr(self, '_last_health_aggregate', {"status": "unknown"})
            state["circuit_breaker"] = self.circuit_breaker.get_status()
            state["degradation_strategy"] = self.degradation_center.get_current_strategy().name if self.degradation_center.get_current_strategy() else None
        except Exception:
            state["health_status"] = {"error": "health_monitor_not_ready"}
            state["circuit_breaker"] = {"error": "circuit_breaker_not_ready"}
            state["degradation_strategy"] = None
        # R008: Expose mode control state
        try:
            self._current_r008_mode = self._map_to_r008_mode()
            state["r008_mode"] = self._current_r008_mode.value
            state["mode_allows_trading"] = self._validate_mode_allows_trading()
            state["mode_transition_count"] = len(self.mode_recorder.get_transition_history())
        except Exception:
            state["r008_mode"] = {"error": "mode_controller_not_ready"}
        return state

# FastAPI WebSocket 伺服器
# ══════════════════════════════════════════════
app    = FastAPI(title="台股 AI 交易系統")
engine = TradingEngine()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

clients: list[WebSocket] = []

@app.on_event("startup")
async def startup():
    engine.connect_shioaji()
    asyncio.create_task(engine.run_loop())
    asyncio.create_task(broadcast_loop())

async def broadcast_loop():
    while True:
        if clients:
            state = engine.get_state()
            msg   = json.dumps(state, ensure_ascii=False, default=str)
            dead  = []
            for ws in clients:
                try:
                    await ws.send_text(msg)
                except:
                    dead.append(ws)
            for ws in dead:
                clients.remove(ws)
        await asyncio.sleep(3)

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    clients.append(ws)
    log.info(f"🔌 前端連線，共 {len(clients)} 個")
    try:
        while True:
            data = await ws.receive_text()
            msg  = json.loads(data)
            # 前端可送指令
            if msg.get("cmd") == "reset":
                engine.risk.reset_daily()
                for sym in WATCH_LIST:
                    engine.signal_eng.reset_vwap(sym)
    except WebSocketDisconnect:
        clients.remove(ws)
        log.info(f"🔌 前端斷線，剩 {len(clients)} 個")

@app.get("/api/state")
def get_state():
    return engine.get_state()

@app.get("/api/trades")
def get_trades():
    return [asdict(t) for t in engine.trades_log]

@app.post("/api/toggle_mode")
def toggle_mode():
    global PAPER_TRADE, AUTO_TRADE
    # R008: Record transition before change
    old_mode = engine._map_to_r008_mode()
    PAPER_TRADE = not PAPER_TRADE
    new_mode = engine._map_to_r008_mode()
    engine._record_mode_transition(old_mode, new_mode, "toggle_mode API called")
    mode = "PAPER" if PAPER_TRADE else "LIVE"
    log.info(f"交易模式切換: {mode} (R008: {old_mode.value} -> {new_mode.value})")
    return {"mode": mode, "paper_trade": PAPER_TRADE}

# R008: Mode transition request model
from pydantic import BaseModel

class ModeTransitionRequest(BaseModel):
    from_mode: str = None
    to_mode: str
    reason: str = "API mode transition request"

@app.get("/api/mode")
def get_mode():
    return {"mode": "PAPER" if PAPER_TRADE else "LIVE", "paper_trade": PAPER_TRADE, "auto_trade": AUTO_TRADE}

@app.post("/api/mode_transition")
def mode_transition(request: ModeTransitionRequest):
    """R008: Mode transition with validation and recording"""
    global PAPER_TRADE, AUTO_TRADE
    
    from_mode_str = (request.from_mode or engine._current_r008_mode.value).lower()
    to_mode_str = (request.to_mode or "").lower()
    reason = request.reason
    
    if not to_mode_str:
        raise HTTPException(status_code=400, detail="to_mode is required")
    
    # Map string to Mode enum
    mode_map = {m.value: m for m in Mode}
    from_mode = mode_map.get(from_mode_str)
    to_mode = mode_map.get(to_mode_str)
    
    if not from_mode or not to_mode:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode. Allowed: {[m.value for m in Mode]}"
        )
    
    # Validate transition
    is_valid, validation_reason = engine.mode_controller.validate_transition(from_mode, to_mode)
    if not is_valid:
        raise HTTPException(
            status_code=403,
            detail=validation_reason
        )
    
    # Check if approval required
    requires_approval = engine.mode_controller.transition_requires_approval(from_mode, to_mode)
    
    # Record transition
    engine._record_mode_transition(from_mode, to_mode, reason)
    engine._current_r008_mode = to_mode
    
    # Map R008 mode back to runtime state
    if to_mode == Mode.SIM:
        PAPER_TRADE = True
    elif to_mode in (Mode.LIVE, Mode.OBSERVE):
        PAPER_TRADE = False
        AUTO_TRADE = (to_mode == Mode.LIVE)
    
    return {
        "status": "success",
        "from_mode": from_mode.value,
        "to_mode": to_mode.value,
        "requires_approval": requires_approval,
        "current_mode": to_mode.value,
        "paper_trade": PAPER_TRADE,
        "auto_trade": AUTO_TRADE
    }

@app.get("/api/mode_history")
def get_mode_history():
    """R008: Get mode transition history"""
    return {
        "transitions": engine.mode_recorder.get_transition_history(),
        "current_mode": engine._current_r008_mode.value
    }

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8765, reload=False)
