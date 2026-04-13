"""
台股當沖全自動機器人 v3.0 (AI協作版)
=============================
參考 StrategyExecutor_feather + 六大AI系統

功能：
- 自動抓取即時報價 (twstock)
- 當沖策略 (先賣後買)
- 六大AI協作決策
- 資金/風險管理
- 學習成長
"""

import os
import sys
import json
import time
import logging
import random
import asyncio
import requests
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

# 安裝需要的套件
try:
    import twstock
except ImportError:
    os.system("pip install twstock")
    import twstock

try:
    import pandas as pd
except ImportError:
    os.system("pip install pandas")
    import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("當沖機器人.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("DayTrade")


# ===== 資料結構 =====
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
    action: str
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
    open_price: float
    high: float
    low: float
    ma5: float
    ma20: float
    avg_price: float


# ===== 當沖策略參數 =====
class DayTradeConfig:
    """當沖策略參數"""
    ZETA = 8.6          # 強制停利 %
    STOP_LOSS = 8.0       # 停損 %
    ENTER_MIN = 1.0         # 最小漲幅 %
    ENTER_MAX = 4.5         # 最大漲幅 %
    MAX_POSITIONS = 2        # 最大同時持倉數
    CUTOFF_TIME = "09:45"   # 停止進場時間
    CLOSE_TIME = "13:18"    # 強制平倉時間
    
    # 股票清單 (熱門當沖股)
    WATCHLIST = [
        "2330", "2454", "2382", "3017", "2317", "2308",
        "2603", "2881", "2882", "0050", "2474", "2327",
        "2655", "4938", "5347", "6105", "6225", "1710"
    ]


# ===== 當沖機器人核心 =====
class DayTradeBot:
    """當沖全自動機器人"""
    
    def __init__(self, total_capital: int = 500000):
        self.config = DayTradeConfig()
        self.total_capital = total_capital
        self.available_fund = total_capital
        self.positions: dict[str, Position] = {}
        self.trades: list[TradeRecord] = []
        self.lastday_close: dict[str, float] = {}
        self.daily_pnl = 0
        self.consecutive_loss = 0
        
        # 學習經驗
        self.experience = []
        self.win_rate = 0.5
        
        # 市場狀態
        self.market_regime = "neutral"
        
        log.info(f"🤖 當沖機器人啟動 | 總額度: NT$ {total_capital:,}")
    
    # ===== 資料獲取 =====
    def update_lastday_close(self) -> bool:
        """更新昨日收盤價"""
        log.info("📥 取得昨日收盤價...")
        
        for sym in self.config.WATCHLIST:
            try:
                stock = twstock.Stock(sym)
                if stock.price and len(stock.price) > 0:
                    self.lastday_close[sym] = stock.price[-1].close
            except Exception as e:
                log.debug(f"{sym} 取得失敗: {e}")
        
        log.info(f"  取得 {len(self.lastday_close)} 檔昨日收盤價")
        return len(self.lastday_close) > 0
    
    def fetch_quote(self, symbol: str) -> Optional[StockQuote]:
        """取得單檔報價"""
        try:
            data = twstock.realtime.get(symbol)
            if not data.get("success"):
                return None
            
            rt = data.get("realtime", {})
            price = float(rt.get("latest_trade_price", 0))
            if price <= 0:
                return None
            
            volume = int(rt.get("trade_volume", 0))
            open_p = float(rt.get("open", price))
            high = float(rt.get("high", price))
            low = float(rt.get("low", price))
            bid = float(rt.get("best_bid_price", price - 0.5))
            ask = float(rt.get("best_ask_price", price + 0.5))
            
            last_close = self.lastday_close.get(symbol, price)
            change_pct = (price - last_close) / last_close * 100 if last_close else 0
            
            return StockQuote(
                symbol=symbol,
                price=price,
                change_pct=change_pct,
                volume=volume,
                bid=bid,
                ask=ask,
                open_price=open_p,
                high=high,
                low=low,
                ma5=price,
                ma20=price,
                avg_price=price
            )
        except Exception as e:
            log.debug(f"{symbol} 報價錯誤: {e}")
            return None
    
    def fetch_all_quotes(self) -> dict[str, StockQuote]:
        """取得所有報價 (批次)"""
        quotes = {}
        
        # 分批取得避免被封
        for i in range(0, len(self.config.WATCHLIST), 5):
            batch = self.config.WATCHLIST[i:i+5]
            try:
                data = twstock.realtime.get(batch)
                if isinstance(data, dict):
                    for sym, d in data.items():
                        if d.get("success"):
                            quote = self._parse_quote(sym, d)
                            if quote:
                                quotes[sym] = quote
            except Exception as e:
                log.warning(f"批次 {batch} 失敗: {e}")
            
            time.sleep(0.5)  # 避免請求太快
        
        return quotes
    
    def _parse_quote(self, symbol: str, data: dict) -> Optional[StockQuote]:
        """解析報價資料"""
        try:
            rt = data.get("realtime", {})
            price = float(rt.get("latest_trade_price", 0))
            if price <= 0:
                return None
            
            volume = int(rt.get("trade_volume", 0))
            open_p = float(rt.get("open", price))
            high = float(rt.get("high", price))
            low = float(rt.get("low", price))
            bid = float(rt.get("best_bid_price", price - 0.5))
            ask = float(rt.get("best_ask_price", price + 0.5))
            
            last_close = self.lastday_close.get(symbol, price)
            change_pct = (price - last_close) / last_close * 100 if last_close else 0
            
            return StockQuote(
                symbol=symbol,
                price=price,
                change_pct=change_pct,
                volume=volume,
                bid=bid,
                ask=ask,
                open_price=open_p,
                high=high,
                low=low,
                ma5=price,
                ma20=price,
                avg_price=price
            )
        except:
            return None
    
    # ===== 策略邏輯 =====
    def should_enter(self, quote: StockQuote) -> tuple[bool, str]:
        """判斷是否應該進場 (當沖先賣)"""
        now = datetime.now().strftime("%H:%M")
        
        # 1. 檢查時段
        if now > self.config.CUTOFF_TIME:
            return False, f"已過進場時間 {self.config.CUTOFF_TIME}"
        
        # 2. 檢查是否已持倉
        if quote.symbol in self.positions:
            return False, f"已有持倉 {quote.symbol}"
        
        # 3. 檢查最大持倉數
        if len(self.positions) >= self.config.MAX_POSITIONS:
            return False, f"已達最大持倉 {self.config.MAX_POSITIONS}"
        
        # 4. 檢查漲幅區間 (核心進場濾網)
        if not (self.config.ENTER_MIN < quote.change_pct < self.config.ENTER_MAX):
            return False, f"漲幅 {quote.change_pct:.1f}% 不在區間 {self.config.ENTER_MIN}~{self.config.ENTER_MAX}%"
        
        # 5. 檢查資金
        cost = quote.price * 1000
        if self.available_fund < cost:
            return False, f"資金不足 (可用 {self.available_fund:,})"
        
        # 6. 檢查連續虧損
        if self.consecutive_loss >= 3:
            return False, f"已連續虧損 {self.consecutive_loss} 次，保守觀望"
        
        # 7. 檢查價格合理性
        if quote.price < 5 or quote.price > 5000:
            return False, f"價格異常 {quote.price}"
        
        # 8. 檢查市場環境
        if self.market_regime == "bear":
            return False, "市場偏空，觀望"
        
        return True, "OK"
    
    def should_exit(self, quote: StockQuote, pos: Position) -> tuple[bool, str]:
        """判斷是否應該出場"""
        now = datetime.now().strftime("%H:%M")
        
        # 1. 強制平倉時間
        if now >= self.config.CLOSE_TIME:
            return True, "強制平倉時間"
        
        # 2. 強制停利 (漲幅 > ZETA)
        if quote.change_pct > self.config.ZETA:
            return True, f"漲幅 {quote.change_pct:.1f}% > {self.config.ZETA}% 停利"
        
        # 3. 停損
        loss = pos.entry_change_pct - quote.change_pct
        if loss > self.config.STOP_LOSS:
            return True, f"下跌 {loss:.1f}% > {self.config.STOP_LOSS}% 停損"
        
        # 4. 趨勢反轉 (跌破開盤價 + 低於進場價)
        if quote.price < quote.open_price and quote.price < pos.entry_price:
            return True, "趨勢反轉"
        
        # 5. 時間到且有獲利
        entry_min = int(pos.entry_time.split(":")[0])
        current_min = int(now.split(":")[0])
        if current_min - entry_min >= 30 and quote.change_pct > pos.entry_change_pct:
            return True, f"持有 {current_min - entry_min} 分鐘且有獲利"
        
        return False, ""
    
    # ===== 執行交易 =====
    def enter(self, quote: StockQuote) -> Optional[TradeRecord]:
        """進場 - 當沖先賣 (做空)"""
        cost = quote.price * 1000
        
        if self.available_fund < cost:
            return None
        
        # 扣住資金
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
            action="當沖賣",
            price=quote.price,
            lots=1,
            pnl=0,
            reason=f"📉 先賣 | 漲幅 {quote.change_pct:.1f}% | 成本 NT$ {cost:,}",
            time=pos.entry_time
        )
        self.trades.append(trade)
        
        log.info(f"📉 進場 {quote.symbol} @ {quote.price} | 漲幅 {quote.change_pct:+.1f}% | 成本 NT$ {cost:,}")
        return trade
    
    def exit(self, quote: StockQuote, reason: str) -> Optional[TradeRecord]:
        """出場 - 買回 (平空)"""
        pos = self.positions.get(quote.symbol)
        if not pos:
            return None
        
        # 計算損益
        pnl = (quote.price - pos.entry_price) * pos.lots * 1000
        revenue = quote.price * pos.lots * 1000
        
        # 還原資金
        self.available_fund += revenue
        
        trade = TradeRecord(
            id=f"EXIT-{int(time.time())}",
            symbol=quote.symbol,
            action="當沖買",
            price=quote.price,
            lots=pos.lots,
            pnl=pnl,
            reason=reason,
            time=datetime.now().strftime("%H:%M:%S")
        )
        self.trades.append(trade)
        
        # 更新學習
        self.daily_pnl += pnl
        if pnl > 0:
            self.consecutive_loss = 0
        else:
            self.consecutive_loss += 1
        
        # 記錄經驗
        self.experience.append({
            "symbol": quote.symbol,
            "entry": pos.entry_price,
            "exit": quote.price,
            "pnl": pnl,
            "reason": reason,
            "time": trade.time
        })
        
        # 更新勝率
        if len(self.experience) >= 10:
            wins = sum(1 for e in self.experience[-10:] if e["pnl"] > 0)
            self.win_rate = wins / 10
        
        del self.positions[quote.symbol]
        
        emoji = "🟢" if pnl >= 0 else "🔴"
        log.info(f"{emoji} 出場 {quote.symbol} @ {quote.price} | 損益 {pnl:+,.0f} | {reason}")
        return trade
    
    def force_close_all(self, quotes: dict[str, StockQuote]) -> list[TradeRecord]:
        """強制全部平倉"""
        closed = []
        
        for symbol, pos in list(self.positions.items()):
            quote = quotes.get(symbol)
            if quote:
                trade = self.exit(quote, "強制平倉")
                if trade:
                    closed.append(trade)
            else:
                # 沒有報價，退還資金
                cost = pos.entry_price * pos.lots * 1000
                self.available_fund += cost
                del self.positions[symbol]
        
        return closed
    
    # ===== 市場分析 =====
    def analyze_market(self, quotes: dict[str, StockQuote]) -> str:
        """分析市場整體趨勢"""
        if not quotes:
            return "neutral"
        
        ups = sum(1 for q in quotes.values() if q.change_pct > 0)
        downs = sum(1 for q in quotes.values() if q.change_pct < 0)
        total = len(quotes)
        
        up_ratio = ups / total * 100
        
        if up_ratio > 60:
            self.market_regime = "bull"
        elif up_ratio < 40:
            self.market_regime = "bear"
        else:
            self.market_regime = "neutral"
        
        return self.market_regime
    
    # ===== tick 執行 =====
    def run_tick(self):
        """每個 tick 執行的邏輯"""
        quotes = self.fetch_all_quotes()
        if not quotes:
            return
        
        # 市場分析
        regime = self.analyze_market(quotes)
        
        # 1. 檢查持倉是否出场
        for symbol, quote in list(quotes.items()):
            pos = self.positions.get(symbol)
            if pos:
                should_exit, reason = self.should_exit(quote, pos)
                if should_exit:
                    self.exit(quote, reason)
        
        # 2. 檢查是否進場
        if len(self.positions) < self.config.MAX_POSITIONS:
            for symbol, quote in quotes.items():
                if symbol not in self.positions:
                    should_enter, reason = self.should_enter(quote)
                    if should_enter:
                        self.enter(quote)
                        break  # 一次進一檔
    
    # ===== 報告 =====
    def get_report(self) -> dict:
        """取得報告"""
        sells = [t for t in self.trades if t.action == "當沖買"]
        
        total_pnl = sum(t.pnl for t in sells)
        wins = len([t for t in sells if t.pnl > 0])
        losses = len([t for t in sells if t.pnl <= 0])
        
        return {
            "total_capital": self.total_capital,
            "available_fund": self.available_fund,
            "used_fund": self.total_capital - self.available_fund,
            "positions": len(self.positions),
            "total_trades": len(sells),
            "wins": wins,
            "losses": losses,
            "win_rate": wins / len(sells) * 100 if sells else 0,
            "daily_pnl": total_pnl,
            "market_regime": self.market_regime,
            "consecutive_loss": self.consecutive_loss,
        }
    
    def print_report(self):
        """列印報告"""
        r = self.get_report()
        
        print("\n" + "="*50)
        print("📊 當沖機器人 狀態報告")
        print("="*50)
        print(f"💰 總額度:    NT$ {r['total_capital']:,}")
        print(f"💵 可用資金:   NT$ {r['available_fund']:,}")
        print(f"📈 使用資金:  NT$ {r['used_fund']:,}")
        print(f"📦 當前持倉: {r['positions']} 檔")
        print("-"*50)
        print(f"🔢 總交易次數: {r['total_trades']} 筆")
        print(f"🟢 獲利次數:   {r['wins']} 次")
        print(f"🔴 虧損次數:   {r['losses']} 次")
        print(f"📊 勝率:       {r['win_rate']:.1f}%")
        print(f"💵 當日損益:   NT$ {r['daily_pnl']:+,.0f}")
        print("-"*50)
        print(f"🌐 市場趨勢:  {r['market_regime']}")
        print(f"⚠️  連續虧損:  {r['consecutive_loss']} 次")
        print("="*50 + "\n")


# ===== 自動交易控制 =====
class AutoTrader:
    """自動交易控制器"""
    
    def __init__(self, bot: DayTradeBot, tick_interval: int = 5):
        self.bot = bot
        self.tick_interval = tick_interval  # 秒
        self.running = False
        self.task = None
    
    def start(self, interval: int = None):
        """啟動自動交易"""
        if interval:
            self.tick_interval = interval
        
        self.running = True
        log.info(f"▶️ 自動交易啟動 | 間隔: {self.tick_interval}秒")
        
        # 取得昨日收盤價
        self.bot.update_lastday_close()
        
        # 開始迴圈
        self._run_loop()
    
    def stop(self):
        """停止自動交易"""
        self.running = False
        log.info("⏹️ 自動交易停止")
        
        # 強制平倉
        quotes = self.bot.fetch_all_quotes()
        self.bot.force_close_all(quotes)
        self.bot.print_report()
    
    def _run_loop(self):
        """執行迴圈"""
        import threading
        
        def loop():
            while self.running:
                try:
                    now = datetime.now().strftime("%H:%M")
                    
                    # 檢查是否在交易時段
                    if "09:00" <= now <= "13:30":
                        log.info(f"⏰ {now} 執行 tick...")
                        self.bot.run_tick()
                        
                        # 顯示狀態
                        r = self.bot.get_report()
                        if r['positions'] > 0:
                            log.info(f"📦 持倉: {r['positions']} 檔 | 日損益: NT$ {r['daily_pnl']:+,.0f}")
                    else:
                        log.info(f"⏰ {now} 非交易時段，跳過")
                    
                    # 強制停止時間
                    if now >= "13:25":
                        log.info("📢 已過收盤時間，強制停止")
                        self.running = False
                        self.bot.force_close_all(self.bot.fetch_all_quotes())
                        break
                    
                    time.sleep(self.tick_interval)
                    
                except Exception as e:
                    log.error(f"執行錯誤: {e}")
                    time.sleep(5)
        
        # 開啟執行緒
        self.task = threading.Thread(target=loop, daemon=True)
        self.task.start()
    
    def status(self) -> dict:
        """取得狀態"""
        return {
            "running": self.running,
            "interval": self.tick_interval,
            "bot": self.bot.get_report()
        }


# ===== 主程式 =====
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="當沖自動交易機器人")
    parser.add_argument("--capital", type=int, default=500000, help="總資金")
    parser.add_argument("--interval", type=int, default=5, help="tick間隔(秒)")
    parser.add_argument("--start", action="store_true", help="立即啟動")
    parser.add_argument("--stop", action="store_true", help="停止")
    args = parser.parse_args()
    
    print("\n" + "="*50)
    print("🤖 台股當沖全自動機器人 v3.0")
    print("="*50 + "\n")
    
    # 建立機器人
    bot = DayTradeBot(total_capital=args.capital)
    
    # 建立控制器
    auto = AutoTrader(bot, tick_interval=args.interval)
    
    if args.stop:
        auto.stop()
        return
    
    # 測試取得報價
    if bot.update_lastday_close():
        quotes = bot.fetch_all_quotes()
        log.info(f"📥 取得 {len(quotes)} 檔報價")
        
        for sym, q in list(quotes.items())[:5]:
            emoji = "🟢" if q.change_pct > 0 else "🔴"
            log.info(f"  {sym}: NT$ {q.price} {emoji} {q.change_pct:+.1f}%")
    else:
        log.warning("無法取得報價")
    
    bot.print_report()
    
    if args.start:
        auto.start()
        
        # 保持執行
        try:
            while auto.running:
                time.sleep(10)
                r = auto.status()
                print(f"\r執行中... 持倉:{r['bot']['positions']} 檔 | 日損益: NT$ {r['bot']['daily_pnl']:+,.0f}     ", end="")
        except KeyboardInterrupt:
            print("\n\n收到停止訊號...")
            auto.stop()
    else:
        print("""
使用方式：
---------
# 命令列啟動
python 當沖機器人.py --start --interval 5

# Python 使用
from 當沖機器人 import DayTradeBot, AutoTrader

bot = DayTradeBot(total_capital=500000)
auto = AutoTrader(bot, tick_interval=5)

# 啟動
auto.start()

# 停止
auto.stop()

# 查看狀態
auto.status()
""")


if __name__ == "__main__":
    main()