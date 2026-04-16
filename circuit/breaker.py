import logging
from enum import Enum
from datetime import datetime, timedelta

class CircuitBreakerState(Enum):
    CLOSED = 1
    OPEN = 2
    HALF_OPEN = 3

class CircuitBreaker:
    def __init__(self, max_daily_loss: float, max_consecutive_losses: int, max_drawdown_pct: float):
        self.state = CircuitBreakerState.CLOSED
        self.max_daily_loss = max_daily_loss
        self.max_consecutive_losses = max_consecutive_losses
        self.max_drawdown_pct = max_drawdown_pct
        self.last_reset_date = datetime.now()
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        self.drawdown_start_date = None
        self.logger = logging.getLogger(__name__)

    def should_block_trade(self) -> bool:
        if self.state == CircuitBreakerState.OPEN:
            return True
        elif self.state == CircuitBreakerState.HALF_OPEN and datetime.now() - self.last_reset_date < timedelta(minutes=1):
            return True
        else:
            return False

    def record_trade_result(self, pnl: float) -> None:
        if pnl < 0:
            self.daily_pnl += pnl
            self.consecutive_losses += 1
            if self.drawdown_start_date is None:
                self.drawdown_start_date = datetime.now()
        else:
            self.consecutive_losses = 0
            if self.drawdown_start_date is not None:
                drawdown_duration = datetime.now() - self.drawdown_start_date
                drawdown_pct = (self.daily_pnl / abs(self.daily_pnl)) * (drawdown_duration.total_seconds() / timedelta(days=1).total_seconds())
                if drawdown_pct > self.max_drawdown_pct:
                    self.logger.warning(f"Drawdown exceeded {self.max_drawdown_pct}%: {drawdown_pct}%")
                self.drawdown_start_date = None

        if self.daily_pnl <= -self.max_daily_loss or self.consecutive_losses >= self.max_consecutive_losses:
            self.state = CircuitBreakerState.OPEN
            self.logger.warning("Circuit breaker opened due to excessive losses or consecutive losses.")
        elif self.state == CircuitBreakerState.OPEN and datetime.now() - self.last_reset_date > timedelta(minutes=1):
            self.state = CircuitBreakerState.HALF_OPEN
            self.logger.info("Circuit breaker transitioning to half-open state.")

    def get_status(self) -> dict:
        return {
            "state": self.state.name,
            "daily_pnl": self.daily_pnl,
            "consecutive_losses": self.consecutive_losses,
            "last_reset_date": self.last_reset_date
        }

# Example usage
if __name__ == "__main__":
    cb = CircuitBreaker(max_daily_loss=5000, max_consecutive_losses=3, max_drawdown_pct=10)
    cb.record_trade_result(-2000)
    cb.record_trade_result(-3000)
    print(cb.get_status())
