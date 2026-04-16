import time
from datetime import datetime

class HealthCheck:
    def check_broker_connection(self):
        # 模擬檢查券商連接
        status = 'ok' if True else 'critical'
        details = "Broker connection is OK" if status == 'ok' else "Broker connection failed"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return {'status': status, 'details': details, 'timestamp': timestamp}

    def check_data_feed(self):
        # 模擬檢查數據供應
        status = 'ok' if True else 'warning'
        details = "Data feed is OK" if status == 'ok' else "Data feed may be delayed"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return {'status': status, 'details': details, 'timestamp': timestamp}

    def check_risk_system(self):
        # 模擬檢查風險系統
        status = 'ok' if True else 'critical'
        details = "Risk system is OK" if status == 'ok' else "Risk system detected a problem"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return {'status': status, 'details': details, 'timestamp': timestamp}

    def check_memory_usage(self):
        # 模擬檢查記憶體使用
        import psutil
        memory = psutil.virtual_memory()
        status = 'ok' if memory.percent < 80 else 'warning'
        details = f"Memory usage is {memory.percent}%" if status == 'ok' else "High memory usage detected"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return {'status': status, 'details': details, 'timestamp': timestamp}

    def check_disk_space(self):
        # 模擬檢查磁碟空間
        import shutil
        disk_usage = shutil.disk_usage("/")
        percent_used = (disk_usage.used / disk_usage.total) * 100
        status = 'ok' if percent_used < 80 else 'warning'
        details = f"Disk space is {percent_used:.1f}%" if status == 'ok' else "Low disk space detected"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return {'status': status, 'details': details, 'timestamp': timestamp}

class HealthMonitor:
    def __init__(self, check_intervals=None, thresholds=None):
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
        self.checker = HealthCheck()

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
