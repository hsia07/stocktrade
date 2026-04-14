"""
TW AI Trading Dashboard
FastAPI + WebSocket + Shioaji

Run:
  pip install -r requirements.txt
  python server.py
"""

import asyncio, json, logging, os, time, math
from datetime import datetime, date
from collections import deque
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Optional
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

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

# ══════════════════════════════════════════════
# 角色一：量化研究員 (Quant Researcher)
# 職責：發現 alpha、設計策略邏輯
# ══════════════════════════════════════════════
class QuantResearcher:
    def __init__(self):
        self.alpha_signals = {}

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

    def run(self, symbol: str, bars: list) -> AgentReport:
        if len(bars) < 30:
            return AgentReport("Backtester", "BT", "idle", "Need more history for backtest", ["Need at least 30 bars"])

        closes = [b["close"] for b in bars]
        trades = []
        in_trade = None

        for i in range(20, len(closes)):
            window = closes[: i + 1]
            ema5  = sum(window[-5:]) / 5
            ema20 = sum(window[-20:]) / 20

            if in_trade is None and ema5 > ema20 * 1.002:
                in_trade = {"entry": closes[i], "idx": i}
            elif in_trade and (ema5 < ema20 or i - in_trade["idx"] >= 30):
                pnl = closes[i] - in_trade["entry"]
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
        self.trades_log: list[TradeRecord] = []
        self.latest_ticks  = {}
        self.agent_reports = {}
        self._shioaji_api  = None
        self._running      = False

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
            ticks = self.mock.tick()
            self.latest_ticks = ticks

            for sym in WATCH_LIST:
                tick  = ticks[sym]
                bars  = list(self.mock.bars[sym])
                bar   = bars[-1] if bars else None
                if bar:
                    self.signal_eng.update_vwap(sym, bar)

                obook = {"bid_vol": tick["bid_vol"], "ask_vol": tick["ask_vol"]}

                self.agent_reports[f"quant_{sym}"]    = asdict(self.quant.analyze(sym, bars))
                self.agent_reports[f"backtest_{sym}"] = asdict(self.backtester.run(sym, bars))
                self.agent_reports[f"signal_{sym}"], sig = self._signal_and_report(sym, bars, tick, obook)
                self.agent_reports["risk"]             = asdict(self.risk.get_report())
                self.agent_reports["execution"]        = asdict(self.execution.get_report())
                self.agent_reports[f"market_{sym}"]    = asdict(self.analyst.analyze(sym, bars, tick))

                if sig and AUTO_TRADE:
                    ok, reason = self.risk.can_enter(sig, tick["price"])
                    if ok:
                        lots = self.risk.calc_lots(sig, tick["price"])
                        if lots > 0:
                            act = "Buy" if sig.direction == Direction.LONG else "Sell"
                            self.execution.place(sym, act, lots, tick["price"], sig.reason)
                            self.risk.on_entry(sig, lots, tick["price"])
                    else:
                        log.info(f"Risk blocked {sym} signal: {reason}")
                elif sig and not AUTO_TRADE:
                    log.info(f"Signal generated for {sym} but AUTO_TRADE is disabled")

                self._manage_positions(sym, tick["price"])

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

    def get_state(self) -> dict:
        return {
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
    PAPER_TRADE = not PAPER_TRADE
    mode = "PAPER" if PAPER_TRADE else "LIVE"
    log.info(f"交易模式切換: {mode}")
    return {"mode": mode, "paper_trade": PAPER_TRADE}

@app.get("/api/mode")
def get_mode():
    return {"mode": "PAPER" if PAPER_TRADE else "LIVE", "paper_trade": PAPER_TRADE, "auto_trade": AUTO_TRADE}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8765, reload=False)
