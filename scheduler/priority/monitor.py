"""
Command Priority Monitor
Round 9: Commands and Task Priority
"""
from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime, timedelta


@dataclass
class PriorityMetrics:
    """Metrics for priority system performance"""
    priority_level: str
    avg_wait_time: float  # seconds
    max_wait_time: float  # seconds
    tasks_executed: int
    tasks_preempted: int


class PriorityMonitor:
    """
    Monitors task priority system to ensure critical tasks aren't delayed
    """
    
    def __init__(self):
        self.metrics_history: List[Dict] = []
        self.alert_thresholds = {
            'critical_max_wait': 1.0,    # 1 second
            'high_max_wait': 5.0,       # 5 seconds
            'queue_saturation': 0.8     # 80% full
        }
    
    def record_execution(self, task_id: str, priority: str, wait_time: float, execution_time: float):
        """Record task execution metrics"""
        self.metrics_history.append({
            'timestamp': datetime.now().isoformat(),
            'task_id': task_id,
            'priority': priority,
            'wait_time': wait_time,
            'execution_time': execution_time
        })
    
    def calculate_metrics(self, window_seconds: int = 300) -> List[PriorityMetrics]:
        """
        Calculate metrics for each priority level
        
        Args:
            window_seconds: Time window for calculation (default 5 minutes)
        """
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        
        # Filter recent metrics
        recent = [m for m in self.metrics_history 
                  if datetime.fromisoformat(m['timestamp']) > cutoff]
        
        # Group by priority
        by_priority = {}
        for m in recent:
            p = m['priority']
            if p not in by_priority:
                by_priority[p] = []
            by_priority[p].append(m)
        
        # Calculate metrics for each priority
        results = []
        for priority, metrics in by_priority.items():
            if metrics:
                wait_times = [m['wait_time'] for m in metrics]
                results.append(PriorityMetrics(
                    priority_level=priority,
                    avg_wait_time=sum(wait_times) / len(wait_times),
                    max_wait_time=max(wait_times),
                    tasks_executed=len(metrics),
                    tasks_preempted=0  # Would track preemptions in real implementation
                ))
        
        return results
    
    def check_alerts(self, queue_status: dict) -> List[str]:
        """
        Check for priority-related alerts
        
        Returns:
            List of alert messages
        """
        alerts = []
        
        # Check queue saturation
        if queue_status.get('total_tasks', 0) / 100 > self.alert_thresholds['queue_saturation']:
            alerts.append("ALERT: Task queue approaching saturation")
        
        # Check wait times from recent metrics
        metrics = self.calculate_metrics(window_seconds=60)  # Last minute
        for m in metrics:
            if m.priority_level == 'CRITICAL' and m.max_wait_time > self.alert_thresholds['critical_max_wait']:
                alerts.append(f"ALERT: Critical tasks waiting too long (max: {m.max_wait_time:.2f}s)")
            elif m.priority_level == 'HIGH' and m.max_wait_time > self.alert_thresholds['high_max_wait']:
                alerts.append(f"WARNING: High priority tasks delayed (max: {m.max_wait_time:.2f}s)")
        
        return alerts
    
    def get_starvation_report(self) -> List[str]:
        """Report any starving low-priority tasks"""
        cutoff = datetime.now() - timedelta(minutes=10)
        old_tasks = [m for m in self.metrics_history 
                     if datetime.fromisoformat(m['timestamp']) < cutoff and not m.get('executed', True)]
        
        report = []
        for task in old_tasks:
            report.append(f"Task {task['task_id']} ({task['priority']}) has been waiting since {task['timestamp']}")
        
        return report
