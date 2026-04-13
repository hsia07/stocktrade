"""
台股 AI 六角色自動交易系統 v3.0
============================
六大 AI 協作系統 - 每個 AI 都有獨立智能，可成長學習

六大角色：
1. 量化研究員 (Quant Researcher) - 數據分析、尋找規律
2. 回測工程師 (Backtest Engineer) - 策略回測、優化參數
3. 風控官 (Risk Officer) - 風險管理、部位控制
4. 信號工程師 (Signal Engineer) - 產生交易訊號
5. 執行工程師 (Execution Engineer) - 執行下單
6. 市場分析師 (Market Analyst) - 市場監控、分析趨勢

協作機制：
- 每個 AI 有自己的記憶庫
- 定期開會（共識決策）
- 學習失敗經驗，優化策略
"""

import os
import json
import time
import logging
import random
import asyncio
import statistics
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, Any
from enum import Enum
from collections import deque

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("六大AI.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("SixAI")


# ===== 基礎資料結構 =====
class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"
    NONE = "none"


@dataclass
class Signal:
    symbol: str
    direction: Direction
    entry_price: float
    stop_loss: float
    target: float
    confidence: float  # 0-100
    reason: str
    ai_source: str  # 哪個 AI 產生的
    timestamp: str = ""


@dataclass
class Position:
    symbol: str
    entry_price: float
    lots: int
    entry_time: str
    direction: Direction
    stop_loss: float
    target: float
    reason: str


@dataclass
class Trade:
    id: str
    symbol: str
    action: str
    price: float
    lots: int
    pnl: float
    reason: str
    ai_source: str
    timestamp: str


@dataclass
class AIFeedback:
    """AI 反饋學習記錄"""
    ai_name: str
    decision: str
    outcome: str
    score: float
    timestamp: str


# ===== 六大 AI 基礎類別 =====
class BaseAI:
    """AI 基礎類別"""
    
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.experience = []  # 經驗庫
        self.decisions = []  # 決策記錄
        self.success_rate = 0.5  # 成功率
        self.learning_rate = 0.1  # 學習率
        
    def record_decision(self, decision: str, outcome: str, score: float):
        """記錄決策和結果"""
        feedback = AIFeedback(
            ai_name=self.name,
            decision=decision,
            outcome=outcome,
            score=score,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.experience.append(feedback)
        self.decisions.append(decision)
        
        # 更新成功率
        if len(self.experience) >= 10:
            recent = self.experience[-10:]
            wins = sum(1 for f in recent if f.score > 0)
            self.success_rate = wins / len(recent)
        
        # 只保留最近 100 筆
        self.experience = self.experience[-100:]
        
    def get_wisdom(self) -> str:
        """從經驗中學習"""
        if len(self.experience) < 5:
            return "經驗不足，無法給出建議"
        
        # 分析最近的決策
        wins = [f for f in self.experience[-10:] if f.score > 0]
        losses = [f for f in self.experience[-10:] if f.score <= 0]
        
        if len(wins) > len(losses):
            return f"近況良好，勝率 {self.success_rate*100:.0f}%，建議積極"
        elif len(wins) < len(losses):
            return f"近況不佳，勝率 {self.success_rate*100:.0f}%，建議保守"
        else:
            return f"平盤，勝率 {self.success_rate*100:.0f}%，維持現狀"


# ===== 角色一：量化研究員 =====
class QuantResearcher(BaseAI):
    """數據分析、尋找規律"""
    
    def __init__(self):
        super().__init__("量化研究員", "分析數據、尋找規律")
        self.factors = {
            "momentum_20d": 0.3,
            "trend_60ma": 0.2,
            "volume_surge": 0.15,
            "rsi": 0.15,
            "bollinger": 0.1,
            "ma_cross": 0.1,
        }
    
    def analyze(self, symbol: str, bars: list) -> dict:
        """分析數據"""
        if len(bars) < 20:
            return {"score": 0, "factors": {}, "signal": "none"}
        
        closes = [b["close"] for b in bars]
        volumes = [b["volume"] for b in bars]
        
        # 動量因子
        momentum = (closes[-1] - closes[-20]) / closes[-20] * 100 if len(closes) >= 20 else 0
        
        # 趨勢因子
        ma20 = sum(closes[-20:]) / 20
        ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else ma20
        trend_score = 1 if closes[-1] > ma60 else 0
        
        # 量能因子
        avg_vol = sum(volumes[-20:]) / 20
        vol_surge = volumes[-1] / avg_vol if avg_vol > 0 else 1
        
        # RSI
        gains = [closes[i] - closes[i-1] for i in range(1, len(closes)) if len(closes) > 1 else []
        avg_gain = sum(max(g, 0) for g in gains[-14:]) / 14
        avg_loss = sum(-min(g, 0) for g in gains[-14:]) / 14
        rsi = 100 - (100 / (1 + avg_gain / (avg_loss + 0.001)))
        
        # 布林帶
        ma = sum(closes[-20:]) / 20
        std = (sum((c - ma) ** 2 for c in closes[-20:]) / 20) ** 0.5
        bb_upper = ma + 2 * std
        bb_lower = ma - 2 * std
        bb_position = (closes[-1] - bb_lower) / (bb_upper - bb_lower + 0.001) * 100
        
        # 計算總分
        score = (
            momentum * self.factors["momentum_20d"] * 10 +
            trend_score * self.factors["trend_60ma"] * 100 +
            (vol_surge - 1) * self.factors["volume_surge"] * 50 +
            (rsi - 50) * self.factors["rsi"] +
            (50 - abs(50 - bb_position)) * self.factors["bollinger"]
        )
        
        # 決定訊號
        if score > 30 and momentum > 0:
            signal = "long"
        elif score < -10 or momentum < -5:
            signal = "short"
        else:
            signal = "none"
        
        result = {
            "score": score,
            "signal": signal,
            "factors": {
                "momentum": momentum,
                "trend": trend_score,
                "volume_surge": vol_surge,
                "rsi": rsi,
                "bb_position": bb_position,
            },
            "confidence": min(abs(score) / 2, 95),
        }
        
        # 記錄決策
        self.record_decision(f"{symbol}:{signal}", "分析", score / 100)
        
        return result


# ===== 角色二：回測工程師 =====
class BacktestEngineer(BaseAI):
    """策略回測、優化參數"""
    
    def __init__(self):
        super().__init__("回測工程師", "策略回測、優化參數")
        self.params = {
            "take_profit": 0.08,
            "stop_loss": 0.06,
            "max_holding_days": 20,
        }
    
    def optimize(self, trades: list) -> dict:
        """根據歷史交易優化參數"""
        if len(trades) < 10:
            return {"params": self.params, "message": "資料不足"}
        
        # 分析損益
        pnls = [t["pnl"] for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        # 計算最佳停利/停損
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        # 根據盈虧比調整
        if avg_win / abs(avg_loss) > 2:
            self.params["take_profit"] = min(self.params["take_profit"] * 1.1, 0.15)
            self.params["stop_loss"] = max(self.params["stop_loss"] * 0.9, 0.03)
        elif avg_win / abs(avg_loss) < 1:
            self.params["take_profit"] = max(self.params["take_profit"] * 0.9, 0.03)
            self.params["stop_loss"] = min(self.params["stop_loss"] * 1.1, 0.1)
        
        message = f"優化完成 | TP:{self.params['take_profit']*100:.0f}% SL:{self.params['stop_loss']*100:.0f}%"
        
        self.record_decision(message, "優化", len(wins) / len(trades))
        
        return {"params": self.params, "message": message}
    
    def backtest(self, symbol: str, bars: list, params: dict) -> dict:
        """回測單一策略"""
        if len(bars) < 30:
            return {"pnl": 0, "trades": 0}
        
        closes = [b["close"] for b in bars]
        trades_test = []
        position = None
        
        for i in range(20, len(closes)):
            ma5 = sum(closes[i-5:i]) / 5
            ma20 = sum(closes[i-20:i]) / 20
            
            # 進場
            if position is None and ma5 > ma20 * 1.01:
                position = {"entry": closes[i], "idx": i}
            
            # 出場
            elif position:
                pnl = 0
                exit_reason = ""
                
                # 停利
                if closes[i] > position["entry"] * (1 + params["take_profit"]):
                    pnl = closes[i] - position["entry"]
                    exit_reason = "停利"
                # 停損
                elif closes[i] < position["entry"] * (1 - params["stop_loss"]):
                    pnl = closes[i] - position["entry"]
                    exit_reason = "停損"
                # 時間到了
                elif i - position["idx"] > params["max_holding_days"]:
                    pnl = closes[i] - position["entry"]
                    exit_reason = "時間"
                
                if pnl != 0:
                    trades_test.append({"pnl": pnl, "reason": exit_reason})
                    position = None
        
        total_pnl = sum(t["pnl"] for t in trades_test)
        
        return {
            "pnl": total_pnl,
            "trades": len(trades_test),
            "win_rate": len([t for t in trades_test if t["pnl"] > 0]) / len(trades_test) * 100 if trades_test else 0
        }


# ===== 角色三：風控官 =====
class RiskOfficer(BaseAI):
    """風險管理、部位控制"""
    
    def __init__(self, total_capital: int = 500000):
        super().__init__("風控官", "風險管理、部位控制")
        self.total_capital = total_capital
        self.available = total_capital
        self.max_daily_loss = 5000
        self.max_position = 2
        self.max_consecutive_loss = 3
        
        self.daily_pnl = 0
        self.consecutive_loss = 0
        self.positions = {}
    
    def can_enter(self, signal: Signal, current_price: float) -> tuple[bool, str]:
        """檢查是否可以進場"""
        # 檢查是否已經持倉
        if signal.symbol in self.positions:
            return False, "已有持倉"
        
        # 檢查最大部位
        if len(self.positions) >= self.max_position:
            return False, "已達最大部位"
        
        # 檢查單日虧損
        if self.daily_pnl < -self.max_daily_loss:
            return False, f"已達單日虧損上限 {self.max_daily_loss}"
        
        # 檢查連續虧損
        if self.consecutive_loss >= self.max_consecutive_loss:
            return False, f"已連續虧損 {self.consecutive_loss} 次"
        
        # 檢查資金
        cost = signal.entry_price * 1000
        if cost > self.available:
            return False, "資金不足"
        
        # 檢查信心度
        if signal.confidence < 60:
            return False, f"信心度 {signal.confidence}% < 60%"
        
        return True, "OK"
    
    def on_trade(self, action: str, pnl: float):
        """記錄交易結果"""
        self.daily_pnl += pnl
        
        if pnl > 0:
            self.consecutive_loss = 0
        else:
            self.consecutive_loss += 1
        
        self.record_decision(f"{action}:{pnl:+.0f}", "交易", pnl / 1000)
    
    def get_status(self) -> dict:
        """取得風控狀態"""
        return {
            "available": self.available,
            "daily_pnl": self.daily_pnl,
            "positions": len(self.positions),
            "consecutive_loss": self.consecutive_loss,
            "risk_level": "high" if self.consecutive_loss >= 2 else "normal",
        }


# ===== 角色四：信號工程師 =====
class SignalEngineer(BaseAI):
    """產生交易訊號"""
    
    def __init__(self):
        super().__init__("信號工程師", "產生交易訊號")
    
    def generate(self, symbol: str, bars: list, quote: dict, quant_result: dict) -> Optional[Signal]:
        """產生訊號"""
        if quant_result["signal"] == "none":
            return None
        
        price = quote.get("price", bars[-1]["close"])
        confidence = quant_result.get("confidence", 50)
        
        # 根據方向決定止損/目標
        if quant_result["signal"] == "long":
            stop_loss = price * 0.97
            target = price * 1.08
            direction = Direction.LONG
            reason = f"多頭訊號 | 動量:{quant_result['factors'].get('momentum', 0):.1f}%"
        else:
            stop_loss = price * 1.03
            target = price * 0.92
            direction = Direction.SHORT
            reason = f"空頭訊號 | 動量:{quant_result['factors'].get('momentum', 0):.1f}%"
        
        signal = Signal(
            symbol=symbol,
            direction=direction,
            entry_price=price,
            stop_loss=stop_loss,
            target=target,
            confidence=confidence,
            reason=reason,
            ai_source=self.name,
        )
        
        self.record_decision(f"{symbol}:{direction}", "訊號", confidence / 100)
        
        return signal


# ===== 角色五：執行工程師 =====
class ExecutionEngineer(BaseAI):
    """執行下單"""
    
    def __init__(self):
        super().__init__("執行工程師", "執行下單")
        self.orders = []
    
    def execute(self, signal: Signal, action: str) -> dict:
        """執行下單"""
        order = {
            "id": f"{action}-{signal.symbol}-{int(time.time())}",
            "symbol": signal.symbol,
            "action": action,
            "price": signal.entry_price,
            "lots": 1,
            "status": "simulated",
            "reason": signal.reason,
            "ai": signal.ai_source,
            "time": datetime.now().strftime("%H:%M:%S")
        }
        
        self.orders.append(order)
        
        self.record_decision(f"{action} {signal.symbol}", "執行", 1 if action == "Buy" else 0.5)
        
        return order
    
    def get_orders(self) -> list:
        return self.orders[-20:]


# ===== 角色六：市場分析師 =====
class MarketAnalyst(BaseAI):
    """市場監控、分析趨勢"""
    
    def __init__(self):
        super().__init__("市場分析師", "市場監控、分析趨勢")
        self.market_regime = "neutral"  # bull / bear / neutral
        self.alerts = []
    
    def analyze_market(self, symbols: list, quotes: dict) -> dict:
        """分析市場整體"""
        if not quotes:
            return {"regime": "neutral", "trend": "不明"}
        
        # 計算市場廣度
        up = sum(1 for q in quotes.values() if q.get("change_pct", 0) > 0)
        down = sum(1 for q in quotes.values() if q.get("change_pct", 0) < 0)
        total = len(quotes)
        
        up_ratio = up / total * 100 if total > 0 else 50
        
        # 判斷趨勢
        if up_ratio > 60:
            self.market_regime = "bull"
            trend = "多頭"
        elif up_ratio < 40:
            self.market_regime = "bear"
            trend = "空頭"
        else:
            self.market_regime = "neutral"
            trend = "盤整"
        
        result = {
            "regime": self.market_regime,
            "trend": trend,
            "up_ratio": up_ratio,
            "symbols": len(quotes),
        }
        
        self.record_decision(f"市場:{trend}", "分析", up_ratio / 100)
        
        return result
    
    def detect_anomaly(self, symbol: str, quote: dict) -> Optional[str]:
        """偵測異常"""
        change = quote.get("change_pct", 0)
        
        if change > 5:
            self.alerts.append(f"{symbol} 漲幅過大 {change:.1f}%")
            return f"漲幅過大 {change:.1f}%"
        elif change < -5:
            self.alerts.append(f"{symbol} 跌幅過大 {change:.1f}%")
            return f"跌幅過大 {change:.1f}%"
        
        return None


# ===== 六大 AI 協作系統 =====
class SixAIBrain:
    """六大 AI 協作大脑"""
    
    def __init__(self, total_capital: int = 500000):
        # 初始化六大 AI
        self.quant = QuantResearcher()
        self.backtest = BacktestEngineer()
        self.risk = RiskOfficer(total_capital)
        self.signal = SignalEngineer()
        self.execution = ExecutionEngineer()
        self.analyst = MarketAnalyst()
        
        self.positions = {}
        self.trades = []
        
        log.info("="*60)
        log.info("六大 AI 系統初始化完成")
        log.info("="*60)
    
    def meeting(self, quotes: dict) -> dict:
        """六大 AI 開會共識"""
        decisions = {}
        
        # 市場分析師先發言
        market = self.analyst.analyze_market(list(quotes.keys()), quotes)
        decisions["analyst"] = market
        
        # 量化研究員分析
        quant_results = {}
        for symbol, quote in quotes.items():
            # 假設有 bars 資料
            bars = [{"close": quote.get("price", 100)}]
            quant_results[symbol] = self.quant.analyze(symbol, bars)
        
        decisions["quant"] = quant_results
        
        # 信號工程師產生訊號
        signals = {}
        for symbol, quote in quotes.items():
            qr = quant_results.get(symbol, {})
            if qr.get("signal") != "none":
                signal = self.signal.generate(symbol, [], quote, qr)
                if signal:
                    signals[symbol] = signal
        
        decisions["signals"] = signals
        
        # 風控官審核
        allowed = {}
        for symbol, signal in signals.items():
            can_enter, reason = self.risk.can_enter(signal, signal.entry_price)
            if can_enter:
                allowed[symbol] = signal
        
        decisions["approved"] = allowed
        
        # 執行
        executed = {}
        for symbol, signal in allowed.items():
            action = "Sell" if signal.direction == Direction.SHORT else "Buy"
            order = self.execution.execute(signal, action)
            executed[symbol] = order
            
            # 建立持倉
            self.positions[symbol] = Position(
                symbol=symbol,
                entry_price=signal.entry_price,
                lots=1,
                entry_time=datetime.now().strftime("%H:%M:%S"),
                direction=signal.direction,
                stop_loss=signal.stop_loss,
                target=signal.target,
                reason=signal.reason
            )
            self.risk.positions[symbol] = self.positions[symbol]
        
        decisions["executed"] = executed
        
        return decisions
    
    def check_positions(self, quotes: dict) -> list:
        """檢查持倉是否需要出場"""
        exits = []
        
        for symbol, pos in list(self.positions.items()):
            quote = quotes.get(symbol)
            if not quote:
                continue
            
            price = quote.get("price", 0)
            
            # 檢查停利/停損
            should_exit = False
            reason = ""
            
            if pos.direction == Direction.LONG:
                if price > pos.target:
                    should_exit = True
                    reason = "停利"
                elif price < pos.stop_loss:
                    should_exit = True
                    reason = "停損"
            else:
                if price < pos.target:
                    should_exit = True
                    reason = "停利"
                elif price > pos.stop_loss:
                    should_exit = True
                    reason = "停損"
            
            if should_exit:
                exits.append({
                    "symbol": symbol,
                    "price": price,
                    "reason": reason,
                    "pnl": (price - pos.entry_price) * pos.lots * 1000
                })
                del self.positions[symbol]
                if symbol in self.risk.positions:
                    del self.risk.positions[symbol]
        
        return exits
    
    def get_report(self) -> dict:
        """取得系統報告"""
        return {
            "risk": self.risk.get_status(),
            "quant_wisdom": self.quant.get_wisdom(),
            "backtest_params": self.backtest.params,
            "positions": len(self.positions),
            "total_trades": len(self.execution.get_orders()),
            "market_regime": self.analyst.market_regime,
        }


# ===== 主程式 =====
def main():
    brain = SixAIBrain(total_capital=500000)
    
    # 模擬報價
    mock_quotes = {
        "2330": {"price": 1050, "change_pct": 2.5},
        "2454": {"price": 1280, "change_pct": 1.2},
        "2382": {"price": 275, "change_pct": -0.8},
    }
    
    # 開會決策
    decisions = brain.meeting(mock_quotes)
    
    log.info("="*60)
    log.info("六大 AI 決策報告")
    log.info("="*60)
    log.info(f"市場趨勢: {decisions['analyst']['trend']}")
    log.info(f"批准訊號: {len(decisions['approved'])} 檔")
    log.info(f"執行交易: {len(decisions['executed'])} 筆")
    
    # 系統報告
    report = brain.get_report()
    log.info(f"\n風險狀態: {report['risk']}")
    log.info(f"量化建議: {report['quant_wisdom']}")
    log.info(f"當前部位: {report['positions']} 檔")


if __name__ == "__main__":
    main()