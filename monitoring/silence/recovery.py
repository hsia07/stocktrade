from dataclasses import dataclass
from enum import Enum
import datetime

class RecoveryStrategy(Enum):
    LOG_ALERT = 1
    NOTIFY_ADMIN = 2
    SWITCH_TO_OBSERVE = 3
    PAUSE_TRADING = 4

@dataclass
class SilenceReport:
    start_time: datetime.datetime
    duration: int  # in minutes

class SilenceRecovery:
    def __init__(self):
        self.recovery_history = []

    def evaluate_and_recover(self, silence_report: SilenceReport) -> RecoveryStrategy:
        escalation_level = self._determine_escalation_level(silence_report.duration)
        strategy = self._get_strategy(escalation_level)

        if strategy == RecoveryStrategy.LOG_ALERT:
            self.log_alert(silence_report)
        elif strategy == RecoveryStrategy.NOTIFY_ADMIN:
            self.notify_admin(silence_report)
        elif strategy == RecoveryStrategy.SWITCH_TO_OBSERVE:
            self.switch_to_observe()
        elif strategy == RecoveryStrategy.PAUSE_TRADING:
            self.pause_trading()

        self.recovery_history.append({
            'start_time': silence_report.start_time,
            'duration': silence_report.duration,
            'strategy': strategy.name
        })
        return strategy

    def _determine_escalation_level(self, duration: int) -> int:
        if duration < 10:
            return 1
        elif duration < 30:
            return 2
        elif duration < 60:
            return 3
        else:
            return 4

    def _get_strategy(self, escalation_level: int) -> RecoveryStrategy:
        strategies = [
            RecoveryStrategy.LOG_ALERT,
            RecoveryStrategy.NOTIFY_ADMIN,
            RecoveryStrategy.SWITCH_TO_OBSERVE,
            RecoveryStrategy.PAUSE_TRADING
        ]
        return strategies[escalation_level - 1]

    def log_alert(self, silence_report: SilenceReport):
        print(f"Alert: System silent for {silence_report.duration} minutes.")

    def notify_admin(self, silence_report: SilenceReport):
        print(f"Admin notification: System silent for {silence_report.duration} minutes.")

    def switch_to_observe(self):
        print("Switching to observe mode.")

    def pause_trading(self):
        print("Pausing trading.")
