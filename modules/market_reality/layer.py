"""
R028: Market Reality Layer - Base Integration (市场现实层-基础集成)
Integrates cost, slippage, fill models with Taiwan market constraints.

Taiwan Market Constraints (±10%, T+2, 集合竞价, 零股/整股):
- 价格涨跌幅限制: ±10% (price limit)
- 结算周期: T+2 (settlement)
- 集合竞价: 08:30-09:00 (pre-market auction)
- 盘中交易: 09:00-13:30 (continuous trading)
- 零股交易: 13:40-14:30 (odd lots, different pricing)
- 整股交易: 1000股为单位 (round lots)
"""

from typing import Dict, Optional, Tuple
from datetime import datetime, time, timedelta
import random


class MarketRealityLayer:
    """
    Market Reality Layer for cost/slippage/fill modeling.
    Enforces Taiwan market constraints (±10%, T+2, 集合竞价, 零股/整股).
    """
    
    def __init__(self):
        # Taiwan market trading sessions
        self.pre_market_auction = (time(8, 30), time(9, 0))
        self.continuous_trading = (time(9, 0), time(13, 30))
        self.odd_lot_trading = (time(13, 40), time(14, 30))
        
        # Taiwan market constraints
        self.price_limit_percent = 0.10  # ±10% price limit
        self.settlement_days = 2  # T+2 settlement
        self.round_lot_size = 1000  # 整股: 1000 shares
        self.odd_lot_max_size = 999  # 零股: <1000 shares
        
        # Cost models
        self.transaction_tax_rate = 0.001425  # Securities transaction tax (sell side)
        self.broker_fee_rate = 0.001425  # Simplified broker fee
        
    def validate_price_limit(self, price: float, reference_price: float) -> Tuple[bool, str]:
        """
        Validate price against ±10% limit.
        Returns: (is_valid, reason)
        """
        price_limit_up = reference_price * (1 + self.price_limit_percent)
        price_limit_down = reference_price * (1 - self.price_limit_percent)
        
        if price > price_limit_up:
            return False, f"PRICE_EXCEEDS_LIMIT_UP: {price} > {price_limit_up}"
        if price < price_limit_down:
            return False, f"PRICE_BELOW_LIMIT_DOWN: {price} < {price_limit_down}"
        return True, "PRICE_WITHIN_LIMIT"
        
    def calculate_costs(self, price: float, volume: int, is_sell: bool = True) -> Dict:
        """
        Calculate total trading costs.
        Taiwan: transaction tax only on sell side.
        """
        trade_value = price * volume
        costs = {
            'trade_value': trade_value,
            'transaction_tax': 0.0,
            'broker_fee': trade_value * self.broker_fee_rate,
            'total_cost': 0.0
        }
        
        if is_sell:
            costs['transaction_tax'] = trade_value * self.transaction_tax_rate
            
        costs['total_cost'] = costs['transaction_tax'] + costs['broker_fee']
        return costs
        
    def estimate_slippage(self, price: float, volume: int, is_odd_lot: bool = False) -> float:
        """
        Estimate slippage based on Taiwan market reality.
        Higher volume → higher slippage.
        Odd lots → higher slippage (less liquidity).
        """
        base_slippage_percent = 0.001  # 0.1% base
        
        # Volume factor: larger volume → higher slippage
        volume_factor = min(volume / self.round_lot_size, 5.0)
        
        # Odd lot penalty: higher slippage for odd lots
        odd_lot_factor = 1.5 if is_odd_lot else 1.0
        
        slippage_percent = base_slippage_percent * volume_factor * odd_lot_factor
        return price * slippage_percent
        
    def estimate_fill_rate(self, volume: int, is_odd_lot: bool = False) -> float:
        """
        Estimate fill rate probability.
        Odd lots have lower fill rates.
        Large volumes may have partial fills.
        """
        if is_odd_lot:
            return random.uniform(0.75, 0.95)  # Lower fill rate for odd lots
        
        if volume > self.round_lot_size * 10:  # Large volume
            return random.uniform(0.85, 0.98)  # Partial fill likely
            
        return random.uniform(0.95, 1.0)  # Normal fill rate
        
    def check_liquidity(self, volume: int, avg_daily_volume: int) -> Tuple[bool, str]:
        """
        Check if liquidity is sufficient.
        Taiwan: wide bid/ask spread or low volume → liquidity insufficient.
        """
        min_volume_threshold = 1000  # Minimum volume for decent liquidity
        
        if volume < min_volume_threshold:
            return False, "LIQUIDITY_INSUFFICIENT_LOW_VOLUME"
            
        # Check if volume is reasonable relative to daily volume
        volume_percent = volume / avg_daily_volume if avg_daily_volume > 0 else 1.0
        if volume_percent > 0.05:  # >5% of daily volume
            return False, "LIQUIDITY_INSUFFICIENT_LARGE_ORDER"
            
        return True, "LIQUIDITY_SUFFICIENT"
        
    def validate_trading_session(self, current_time: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Check if current time is in valid Taiwan market trading session.
        """
        if current_time is None:
            current_time = datetime.now()
            
        current_time_only = current_time.time()
        
        # Check 集合竞价 (pre-market auction)
        if self.pre_market_auction[0] <= current_time_only <= self.pre_market_auction[1]:
            return True, "PRE_MARKET_AUCTION"
            
        # Check 盘中交易 (continuous trading)
        if self.continuous_trading[0] <= current_time_only <= self.continuous_trading[1]:
            return True, "CONTINUOUS_TRADING"
            
        # Check 零股交易 (odd lot trading)
        if self.odd_lot_trading[0] <= current_time_only <= self.odd_lot_trading[1]:
            return True, "ODD_LOT_TRADING"
            
        return False, "OUTSIDE_TRADING_HOURS"
        
    def is_odd_lot(self, volume: int) -> bool:
        """Check if volume is odd lot (零股)."""
        return volume < self.round_lot_size
        
    def calculate_settlement_date(self, trade_date: Optional[datetime] = None) -> datetime:
        """
        Calculate T+2 settlement date.
        Taiwan: T+2 settlement cycle.
        """
        if trade_date is None:
            trade_date = datetime.now()
        return trade_date + timedelta(days=self.settlement_days)
        
    def evaluate_order(self, price: float, volume: int, reference_price: float,
                      avg_daily_volume: int = 100000) -> Dict:
        """
        Comprehensive order evaluation against Market Reality Layer.
        Returns: evaluation result with costs, slippage, fill rate, constraints.
        """
        results = {
            'passed': True,
            'reasons': [],
            'constraints': {},
            'costs': {},
            'slippage': 0.0,
            'fill_rate': 1.0,
            'liquidity_sufficient': True
        }
        
        # 1. Validate price limit (±10%)
        is_valid_price, price_reason = self.validate_price_limit(price, reference_price)
        results['constraints']['price_limit'] = {
            'passed': is_valid_price,
            'reason': price_reason,
            'limit_up': reference_price * (1 + self.price_limit_percent),
            'limit_down': reference_price * (1 - self.price_limit_percent)
        }
        if not is_valid_price:
            results['passed'] = False
            results['reasons'].append(price_reason)
            
        # 2. Check odd lot vs round lot
        is_odd = self.is_odd_lot(volume)
        results['constraints']['lot_type'] = 'ODD_LOT' if is_odd else 'ROUND_LOT'
        
        # 3. Calculate costs
        results['costs'] = self.calculate_costs(price, volume)
        
        # 4. Estimate slippage
        results['slippage'] = self.estimate_slippage(price, volume, is_odd)
        
        # 5. Estimate fill rate
        results['fill_rate'] = self.estimate_fill_rate(volume, is_odd)
        
        # 6. Check liquidity
        is_liquid, liquidity_reason = self.check_liquidity(volume, avg_daily_volume)
        results['liquidity_sufficient'] = is_liquid
        if not is_liquid:
            results['passed'] = False
            results['reasons'].append(liquidity_reason)
            
        # 7. Validate trading session
        is_valid_session, session_reason = self.validate_trading_session()
        results['constraints']['trading_session'] = {
            'passed': is_valid_session,
            'reason': session_reason
        }
        if not is_valid_session:
            results['passed'] = False
            results['reasons'].append(session_reason)
            
        # 8. Calculate T+2 settlement
        results['constraints']['settlement_date'] = self.calculate_settlement_date()
        results['constraints']['settlement_cycle'] = f"T+{self.settlement_days}"
        
        return results
