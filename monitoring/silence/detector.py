from datetime import datetime, timedelta

class SilenceDetector:
    def __init__(self, market_data_timeout=30, trades_timeout=60, heartbeat_timeout=300):
        self.market_data_timeout = timedelta(seconds=market_data_timeout)
        self.trades_timeout = timedelta(seconds=trades_timeout)
        self.heartbeat_timeout = timedelta(seconds=heartbeat_timeout)
        
        self.last_market_data_update = None
        self.last_trades_update = None
        self.last_heartbeat_update = None

    def update_market_data(self):
        self.last_market_data_update = datetime.now()

    def update_trades(self):
        self.last_trades_update = datetime.now()

    def update_heartbeat(self):
        self.last_heartbeat_update = datetime.now()

    def is_silent(self):
        if (self.last_market_data_update and
            datetime.now() - self.last_market_data_update > self.market_data_timeout):
            return True
        if (self.last_trades_update and
            datetime.now() - self.last_trades_update > self.trades_timeout):
            return True
        if (self.last_heartbeat_update and
            datetime.now() - self.last_heartbeat_update > self.heartbeat_timeout):
            return True
        return False

    def get_silence_report(self):
        report = {}
        if self.last_market_data_update:
            report['market_data'] = (datetime.now() - self.last_market_data_update).total_seconds()
        else:
            report['market_data'] = 'Never updated'
        
        if self.last_trades_update:
            report['trades'] = (datetime.now() - self.last_trades_update).total_seconds()
        else:
            report['trades'] = 'Never updated'
        
        if self.last_heartbeat_update:
            report['heartbeat'] = (datetime.now() - self.last_heartbeat_update).total_seconds()
        else:
            report['heartbeat'] = 'Never updated'
        
        return report

    def reset(self):
        self.last_market_data_update = None
        self.last_trades_update = None
        self.last_heartbeat_update = None
