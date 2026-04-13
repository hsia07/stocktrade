"""
台股當沖全自動機器人 v1.0
================
參考: StrategyExecutor_feather + tw_stocker

功能：
- 自動抓取即時報價 (twstock)
- 當沖策略進場濾網
- 固定停利/停損
- 資金控管
- 13:30 強制平倉
"""

import os
import time
import json
import logging
import random
import asyncio
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional
from enum import Enum

try:
    import twstock
except ImportError:
    twstock = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("daytrade.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("DayTrade")


class Direction(str, Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class Position:
    symbol: str
    entry_price: float
    lots: int
    entry_time: str
    direction: str
    entry_change_pct: float


@dataclass
class TradeRecord:
    id: str
    symbol: str
    action: str  # Sell (當沖先賣) / Buy (買回)
    price: float
    lots: int
    pnl: float
    reason: str
    time: str


@dataclass
class StockQuote:
    symbol: str
    price: float
    change_pct: float
    volume: int
    bid: float
    ask: float
    ma5: float
    ma20: float
    avg_price: float


class DayTradeBot:
    """當沖機器人"""
    
    # ===== 策略參數 =====
    ZETA = 8.6  # 強制停利 %
    STOP_LOSS = 8.0  # 停損 %
    ENTER_MIN = 1.0  # 最小漲幅 %
    ENTER_MAX = 4.5  # 最大漲幅 %
    MAX_POSITIONS = 2  # 最大同時持倉數
    CUTOFF_TIME = "09:45"  # 停止進場時間
    CLOSE_TIME = "13:18"  # 強制平倉時間
    
    def __init__(self, total_capital: int = 500000):
        self.total_capital = total_capital
        self.available_fund = total_capital
        self.positions: dict[str, Position] = {}
        self.trades: list[TradeRecord] = []
        self.lastday_close: dict[str, float] = {}
        
        # 監控股票清單
        self.watchlist = [
            "2330", "2454", "2382", "3017", "2317", "2308",
            "2603", "2881", "2882", "0050"
        ]
        
        log.info(f"當沖機器人啟動 | 總額度: {total_capital}")
    
    def update_lastday_close(self):
        """更新昨日收盤價"""
        if not twstock:
            log.warning("twstock 未安裝")
            return
        
        for sym in self.watchlist:
            try:
                stock = twstock.Stock(sym)
                if stock.price:
                    self.lastday_close[sym] = stock.price[-1].close
            except Exception as e:
                log.warning(f"{sym} 取得昨日收盤失敗: {e}")
        
        log.info(f"昨日收盤: {self.lastday_close}")
    
    def fetch_quote(self, symbol: str) -> Optional[StockQuote]:
        """取得單檔報價"""
        if not twstock:
            return None
        
        try:
            data = twstock.realtime.get(symbol)
            if not data.get("success"):
                return None
            
            rt = data.get("realtime", {})
            price = float(rt.get("latest_trade_price", 0))
            if price <= 0:
                return None
            
            volume = int(rt.get("trade_volume", 0))
            last_close = self.lastday_close.get(symbol, price)
            change_pct = (price - last_close) / last_close * 100 if last_close else 0
            
            # 計算均價
            avg_price = price  # 簡化
            
            return StockQuote(
                symbol=symbol,
                price=price,
                change_pct=change_pct,
                volume=volume,
                bid=price - 0.5,
                ask=price + 0.5,
                ma5=price,
                ma20=price,
                avg_price=avg_price
            )
        except Exception as e:
            log.debug(f"{symbol} 取得報價失敗: {e}")
            return None
    
    def fetch_all_quotes(self) -> dict[str, StockQuote]:
        """取得所有報價"""
        quotes = {}
        
        if not twstock:
            return quotes
        
        # 分批取得
        for i in range(0, len(self.watchlist), 10):
            batch = self.watchlist[i:i+10]
            try:
                data = twstock.realtime.get(batch)
                for sym, d in data.items():
                    if d.get("success"):
                        rt = d.get("realtime", {})
                        price = float(rt.get("latest_trade_price", 0))
                        if price > 0:
                            last_close = self.lastday_close.get(sym, price)
                            change_pct = (price - last_close) / last_close * 100 if last_close else 0
                            quotes[sym] = StockQuote(
                                symbol=sym,
                                price=price,
                                change_pct=change_pct,
                                volume=int(rt.get("trade_volume", 0)),
                                bid=price - 0.5,
                                ask=price + 0.5,
                                ma5=price,
                                ma20=price,
                                avg_price=price
                            )
            except Exception as e:
                log.warning(f"批次取得失敗: {e}")
        
        return quotes
    
    def should_enter(self, quote: StockQuote, pos: Optional[Position]) -> tuple[bool, str]:
        """判斷是否應該進場"""
        now = datetime.now().strftime("%H:%M")
        
        # 非交易時段
        if now > self.CUTOFF_TIME:
            return False, f"已過進場時間 {self.CUTOFF_TIME}"
        
        # 已有持倉
        if pos:
            return False, f"已有持倉 {pos.symbol}"
        
        # 超過最大持倉數
        if len(self.positions) >= self.MAX_POSITIONS:
            return False, f"已達最大持倉 {self.MAX_POSITIONS}"
        
        # 漲幅不在區間
        if not (self.ENTER_MIN < quote.change_pct < self.ENTER_MAX):
            return False, f"漲幅 {quote.change_pct:.1f}% 不在區間"
        
        # 資金不足
        cost = quote.price * 1000
        if self.available_fund < cost:
            return False, f"資金不足 {self.available_fund}"
        
        # 低於平均價 (進場濾網)
        if quote.price >= quote.avg_price:
            return False, f"價格 {price} >= 均價"
        
        return True, "OK"
    
    def should_exit(self, quote: StockQuote, pos: Position) -> tuple[bool, str]:
        """判斷是否應該出場"""
        now = datetime.now().strftime("%H:%M")
        
        # 強制平倉時間
        if now >= self.CLOSE_TIME:
            return True, "強制平倉時間"
        
        # 強制停利 (漲幅 > ZETA)
        if quote.change_pct > self.ZETA:
            return True, f"漲幅 {quote.change_pct:.1f}% > {self.ZETA}% 停利"
        
        # 停損
        if quote.change_pct < pos.entry_change_pct - self.STOP_LOSS:
            return True, f"下跌 {pos.entry_change_pct - quote.change_pct:.1f}% > {self.STOP_LOSS}% 停損"
        
        # 趨勢反轉 (低於均價 + 低於進場價)
        if quote.price < quote.avg_price and quote.price < pos.entry_price:
            return True, "趨勢反轉"
        
        return False, ""
    
    def enter(self, quote: StockQuote) -> Optional[TradeRecord]:
        """進場 - 當沖先賣"""
        cost = quote.price * 1000
        
        if self.available_fund < cost:
            return None
        
        self.available_fund -= cost
        
        pos = Position(
            symbol=quote.symbol,
            entry_price=quote.price,
            lots=1,
            entry_time=datetime.now().strftime("%H:%M:%S"),
            direction="short",
            entry_change_pct=quote.change_pct
        )
        self.positions[quote.symbol] = pos
        
        trade = TradeRecord(
            id=f"ENTER-{int(time.time())}",
            symbol=quote.symbol,
            action="Sell",  # 當沖先賣
            price=quote.price,
            lots=1,
            pnl=0,
            reason=f"當沖賣出 | 漲幅 {quote.change_pct:.1f}% | 成本 {cost}",
            time=pos.entry_time
        )
        self.trades.append(trade)
        
        log.info(f"📉 進場 {quote.symbol} @ {quote.price} | 漲幅 {quote.change_pct:.1f}%")
        return trade
    
    def exit(self, quote: StockQuote, reason: str) -> Optional[TradeRecord]:
        """出场 - 買回"""
        pos = self.positions.get(quote.symbol)
        if not pos:
            return None
        
        pnl = (quote.price - pos.entry_price) * pos.lots * 1000
        revenue = quote.price * pos.lots * 1000
        self.available_fund += revenue
        
        trade = TradeRecord(
            id=f"EXIT-{int(time.time())}",
            symbol=quote.symbol,
            action="Buy",  # 買回
            price=quote.price,
            lots=pos.lots,
            pnl=pnl,
            reason=reason,
            time=datetime.now().strftime("%H:%M:%S")
        )
        self.trades.append(trade)
        
        del self.positions[quote.symbol]
        
        log.info(f"📗 出場 {quote.symbol} @ {quote.price} | 損益 {pnl:+.0f} | {reason}")
        return trade
    
    def close_all(self, quotes: dict[str, StockQuote]) -> list[TradeRecord]:
        """強制全部平倉"""
        closed = []
        
        for sym, pos in list(self.positions.items()):
            quote = quotes.get(sym)
            if quote:
                trade = self.exit(quote, "強制平倉")
                if trade:
                    closed.append(trade)
            else:
                # 沒有報價直接���放資金
                cost = pos.entry_price * pos.lots * 1000
                self.available_fund += cost
                del self.positions[sym]
        
        return closed
    
    def get_report(self) -> dict:
        """取得報告"""
        sells = [t for t in self.trades if t.action == "Sell"]
        buys = [t for t in self.trades if t.action == "Buy"]
        
        total_pnl = sum(t.pnl for t in buys)
        wins = len([t for t in buys if t.pnl > 0])
        losses = len([t for t in buys if t.pnl <= 0])
        
        return {
            "total_capital": self.total_capital,
            "available_fund": self.available_fund,
            "used_fund": self.total_capital - self.available_fund,
            "positions": len(self.positions),
            "total_trades": len(buys),
            "wins": wins,
            "losses": losses,
            "win_rate": wins / len(buys) * 100 if buys else 0,
            "total_pnl": total_pnl,
        }
    
    def run_tick(self):
        """每次 Tick 執行的邏輯"""
        quotes = self.fetch_all_quotes()
        if not quotes:
            return
        
        # 檢查出场
        for sym, quote in quotes.items():
            pos = self.positions.get(sym)
            if pos:
                should_exit, reason = self.should_exit(quote, pos)
                if should_exit:
                    self.exit(quote, reason)
        
        # 檢查進場
        if len(self.positions) < self.MAX_POSITIONS:
            for sym, quote in quotes.items():
                pos = self.positions.get(sym)
                should_enter, reason = self.should_enter(quote, pos)
                if should_enter:
                    self.enter(quote)
                    break  # 一次進一檔


# ===== 主程式 =====
def main():
    bot = DayTradeBot(total_capital=500000)
    bot.update_lastday_close()
    
    log.info("="*50)
    log.info("當沖機器人準備就緒")
    log.info(f"監控股票: {bot.watchlist}")
    log.info(f"額度: {bot.total_capital}")
    log.info("="*50)
    
    # 示例：單次報價測試
    quotes = bot.fetch_all_quotes()
    log.info(f"取得報價: {len(quotes)} 檔")
    
    for sym, q in list(quotes.items())[:3]:
        log.info(f"  {sym}: {q.price} ({q.change_pct:+.1f}%)")


if __name__ == "__main__":
    main()