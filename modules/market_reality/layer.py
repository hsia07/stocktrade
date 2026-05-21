"""
R028: Market Reality Layer - Base Integration (市场现实层-基础集成)
Integrates cost, slippage, fill models with Taiwan market constraints.

Taiwan Market Constraints (±10%, T+2, 集合竞价, 零股/整股):
- 价格涨跌幅限制: ±10% (price limit)
- 结算周期: T+2 (settlement)
- 集合竞价: 08:30-09:00 (pre-market auction)
- 盘中交易: 09:00-13:30 (continuous trading)
- 盘后竞价: 13:30-13:35 (closing auction)
- 零股交易: 13:40-14:30 (odd lots, different pricing)
- 整股交易: 1000股为单位 (round lots)
"""

from typing import Dict, Optional, Tuple
from datetime import datetime, time, timedelta, date


class MarketRealityLayer:
    """
    Market Reality Layer for cost/slippage/fill modeling.
    Enforces Taiwan market constraints (±10%, T+2, 集合竞价, 零股/整股).
    """

    def __init__(self, holiday_dates: Optional[set] = None):
        self.holiday_dates: set = holiday_dates if holiday_dates else set()

        self.pre_market_auction = (time(8, 30), time(9, 0))
        self.continuous_trading = (time(9, 0), time(13, 30))
        self.closing_auction = (time(13, 30), time(13, 35))
        self.odd_lot_trading = (time(13, 40), time(14, 30))

        self.price_limit_percent = 0.10
        self.settlement_days = 2
        self.round_lot_size = 1000
        self.odd_lot_max_size = 999

        self.transaction_tax_rate = 0.001425
        self.broker_fee_rate = 0.001425

    def add_holiday(self, holiday_date: date) -> None:
        """Inject a Taiwan market holiday date. holiday_dates set is consumer-managed."""
        self.holiday_dates.add(holiday_date)

    def _is_non_trading_day(self, d: date) -> bool:
        """Check if date is a weekend or injected holiday. Returns True for non-trading day."""
        if d.weekday() >= 5:
            return True
        if d in self.holiday_dates:
            return True
        return False

    def validate_trading_session(self, current_time: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Check if current time is in valid Taiwan market trading session.
        - Weekend (Saturday/Sunday) → blocked NON_TRADING_DAY
        - Injected holiday → blocked NON_TRADING_DAY
        - current_time is None → fail-closed SESSION_UNKNOWN
        - Non-datetime type → fail-closed SESSION_UNKNOWN
        - Time band checks: pre-market auction, continuous, closing auction, odd-lot
        """
        if current_time is None:
            return False, "SESSION_UNKNOWN"

        if not isinstance(current_time, datetime):
            return False, "SESSION_UNKNOWN"

        d = current_time.date()
        if self._is_non_trading_day(d):
            return False, "NON_TRADING_DAY"

        current_time_only = current_time.time()

        if self.pre_market_auction[0] <= current_time_only <= self.pre_market_auction[1]:
            return True, "PRE_MARKET_AUCTION"

        if self.continuous_trading[0] <= current_time_only < self.closing_auction[0]:
            return True, "CONTINUOUS_TRADING"

        if self.closing_auction[0] <= current_time_only <= self.closing_auction[1]:
            return True, "CLOSING_AUCTION"

        if self.odd_lot_trading[0] <= current_time_only <= self.odd_lot_trading[1]:
            return True, "ODD_LOT_TRADING"

        return False, "OUTSIDE_TRADING_HOURS"
        
    def evaluate_order(self, price: float, volume: int, reference_price: float,
                      avg_daily_volume: int = 100000,
                      current_time: Optional[datetime] = None) -> Dict:
        """
        Comprehensive order evaluation against Market Reality Layer.
        current_time parameter enables backtest/replay injection of historical timestamps.
        If current_time is None, uses wall-clock (legacy fallback, not recommended for backtest).
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

        is_odd = self.is_odd_lot(volume)
        results['constraints']['lot_type'] = 'ODD_LOT' if is_odd else 'ROUND_LOT'

        results['costs'] = self.calculate_costs(price, volume)
        results['slippage'] = self.estimate_slippage(price, volume, is_odd)
        results['fill_rate'] = self.estimate_fill_rate(volume, is_odd)

        is_liquid, liquidity_reason = self.check_liquidity(volume, avg_daily_volume)
        results['liquidity_sufficient'] = is_liquid
        if not is_liquid:
            results['passed'] = False
            results['reasons'].append(liquidity_reason)

        is_valid_session, session_reason = self.validate_trading_session(current_time)
        results['constraints']['trading_session'] = {
            'passed': is_valid_session,
            'reason': session_reason
        }
        if not is_valid_session:
            results['passed'] = False
            results['reasons'].append(session_reason)

        results['constraints']['settlement_date'] = self.calculate_settlement_date()
        results['constraints']['settlement_cycle'] = f"T+{self.settlement_days}"

        return results

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

    def check_liquidity(self, volume: int, avg_daily_volume: int) -> Tuple[bool, str]:
        """
        Check if liquidity is sufficient.
        Taiwan: wide bid/ask spread or low volume → liquidity insufficient.
        """
        min_volume_threshold = 1000

        if volume < min_volume_threshold:
            return False, "LIQUIDITY_INSUFFICIENT_LOW_VOLUME"

        volume_percent = volume / avg_daily_volume if avg_daily_volume > 0 else 1.0
        if volume_percent > 0.05:
            return False, "LIQUIDITY_INSUFFICIENT_LARGE_ORDER"

        return True, "LIQUIDITY_SUFFICIENT"

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
        base_slippage_percent = 0.001

        volume_factor = min(volume / self.round_lot_size, 5.0)
        odd_lot_factor = 1.5 if is_odd_lot else 1.0

        slippage_percent = base_slippage_percent * volume_factor * odd_lot_factor
        return price * slippage_percent

    def estimate_fill_rate(self, volume: int, is_odd_lot: bool = False) -> float:
        """
        Estimate fill rate probability (deterministic).
        Odd lots have lower fill rates. Large volumes may have partial fills.
        Returns deterministic probability based on volume and lot type only.
        No random, no time-dependence.
        """
        if is_odd_lot:
            return 0.80
        if volume > self.round_lot_size * 10:
            return 0.85
        return 0.97
