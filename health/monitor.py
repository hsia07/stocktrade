import os
import time
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict, Any


class HealthCheck:
    def __init__(
        self,
        broker_probe: Optional[Callable[[], bool]] = None,
        data_feed_probe: Optional[Callable[[], bool]] = None,
        risk_system_probe: Optional[Callable[[], bool]] = None,
    ):
        self._broker_probe = broker_probe
        self._data_feed_probe = data_feed_probe
        self._risk_system_probe = risk_system_probe

    def check_broker_connection(self) -> Dict[str, Any]:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if self._broker_probe is None:
            return {
                'status': 'degraded',
                'details': 'Broker probe not configured — degraded mode',
                'timestamp': timestamp,
            }
        try:
            result = self._broker_probe()
            if result is True:
                return {'status': 'ok', 'details': 'Broker connection OK', 'timestamp': timestamp}
            else:
                return {'status': 'critical', 'details': 'Broker probe returned False', 'timestamp': timestamp}
        except Exception as e:
            return {'status': 'critical', 'details': f'Broker probe exception: {e}', 'timestamp': timestamp}

    def check_data_feed(self) -> Dict[str, Any]:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if self._data_feed_probe is None:
            return {
                'status': 'degraded',
                'details': 'Data feed probe not configured — degraded mode',
                'timestamp': timestamp,
            }
        try:
            result = self._data_feed_probe()
            if result is True:
                return {'status': 'ok', 'details': 'Data feed OK', 'timestamp': timestamp}
            else:
                return {'status': 'warning', 'details': 'Data feed probe returned False', 'timestamp': timestamp}
        except Exception as e:
            return {'status': 'warning', 'details': f'Data feed probe exception: {e}', 'timestamp': timestamp}

    def check_risk_system(self) -> Dict[str, Any]:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if self._risk_system_probe is None:
            return {
                'status': 'degraded',
                'details': 'Risk system probe not configured — degraded mode',
                'timestamp': timestamp,
            }
        try:
            result = self._risk_system_probe()
            if result is True:
                return {'status': 'ok', 'details': 'Risk system OK', 'timestamp': timestamp}
            else:
                return {'status': 'critical', 'details': 'Risk system probe returned False', 'timestamp': timestamp}
        except Exception as e:
            return {'status': 'critical', 'details': f'Risk system probe exception: {e}', 'timestamp': timestamp}

    def check_memory_usage(self) -> Dict[str, Any]:
        try:
            import psutil
            memory = psutil.virtual_memory()
            status = 'ok' if memory.percent < 80 else 'warning'
            details = f"Memory usage is {memory.percent}%" if status == 'ok' else "High memory usage detected"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return {'status': status, 'details': details, 'timestamp': timestamp}
        except ImportError:
            return {
                'status': 'warning',
                'details': 'Memory check skipped: psutil not available (install with: pip install psutil)',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

    def check_disk_space(self) -> Dict[str, Any]:
        import shutil
        disk_usage = shutil.disk_usage("/")
        percent_used = (disk_usage.used / disk_usage.total) * 100
        status = 'ok' if percent_used < 80 else 'warning'
        details = f"Disk space is {percent_used:.1f}%" if status == 'ok' else "Low disk space detected"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return {'status': status, 'details': details, 'timestamp': timestamp}


class HealthMonitor:
    def __init__(self, check_intervals=None, thresholds=None,
                 broker_probe=None, data_feed_probe=None, risk_system_probe=None):
        self.check_intervals = check_intervals or {
            'broker_connection': 60,
            'data_feed': 300,
            'risk_system': 300,
            'memory_usage': 300,
            'disk_space': 300
        }
        self.thresholds = thresholds or {
            'memory_usage': 80,
            'disk_space': 80
        }
        self.checker = HealthCheck(
            broker_probe=broker_probe,
            data_feed_probe=data_feed_probe,
            risk_system_probe=risk_system_probe,
        )

    def run_checks(self):
        checks = [
            ('broker_connection', self.checker.check_broker_connection),
            ('data_feed', self.checker.check_data_feed),
            ('risk_system', self.checker.check_risk_system),
            ('memory_usage', self.checker.check_memory_usage),
            ('disk_space', self.checker.check_disk_space)
        ]
        results = {}
        for name, check in checks:
            result = check()
            results[name] = result
            if result['status'] == 'critical':
                print(f"Critical error: {result['details']} at {result['timestamp']}")
        return results

    def aggregate_status(self, results):
        critical_count = sum(1 for result in results.values() if result['status'] == 'critical')
        warning_count = sum(1 for result in results.values() if result['status'] == 'warning')
        total_checks = len(results)
        overall_status = 'ok' if critical_count == 0 else 'critical'
        details = f"Total checks: {total_checks}, Critical: {critical_count}, Warning: {warning_count}"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return {'status': overall_status, 'details': details, 'timestamp': timestamp}


if __name__ == '__main__':
    monitor = HealthMonitor()
    results = monitor.run_checks()
    print(monitor.aggregate_status(results))