from enum import Enum

class DegradationStrategy(Enum):
    PAUSE_TRADING = 1
    SWITCH_TO_PAPER = 2
    REDUCE_POSITION_SIZE = 3
    DISABLE_AI = 4

class DegradationCenter:
    def __init__(self):
        self.current_strategy = None
        self.history = []

    def evaluate_and_degrade(self, health_status):
        if not health_status.is_healthy():
            if self.current_strategy != DegradationStrategy.PAUSE_TRADING:
                self.current_strategy = DegradationStrategy.PAUSE_TRADING
                self.history.append((DegradationStrategy.PAUSE_TRADING, "Trading paused due to health issues."))
            elif health_status.has_paper_trading_enabled():
                self.current_strategy = DegradationStrategy.SWITCH_TO_PAPER
                self.history.append((DegradationStrategy.SWITCH_TO_PAPER, "Switched to paper trading due to health issues."))
            else:
                self.current_strategy = DegradationStrategy.REDUCE_POSITION_SIZE
                self.history.append((DegradationStrategy.REDUCE_POSITION_SIZE, "Reduced position size due to health issues."))
        elif self.current_strategy is not None:
            self.restore()
            self.history.append((None, "System restored to normal operation."))

    def restore(self):
        self.current_strategy = None

    def get_current_strategy(self):
        return self.current_strategy

class HealthStatus:
    def __init__(self, is_healthy=True, has_paper_trading_enabled=False):
        self.is_healthy = is_healthy
        self.has_paper_trading_enabled = has_paper_trading_enabled

    def is_healthy(self):
        return self.is_healthy

    def has_paper_trading_enabled(self):
        return self.has_paper_trading_enabled
