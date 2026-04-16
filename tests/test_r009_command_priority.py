"""
Round 9 Tests: Commands and Task Priority
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta

from scheduler.priority.scheduler import PriorityScheduler, Priority, Task, TaskType, CommandRouter
from scheduler.priority.monitor import PriorityMonitor, PriorityMetrics


class TestPriorityScheduler:
    """Test priority scheduler functionality"""
    
    def test_scheduler_initialization(self):
        """Scheduler initializes with empty queue"""
        scheduler = PriorityScheduler()
        
        assert len(scheduler.task_queue) == 0
        assert scheduler.max_queue_size == 100
    
    def test_submit_task(self):
        """Tasks can be submitted to queue"""
        scheduler = PriorityScheduler()
        
        task = Task(
            id="task-001",
            name="Test Task",
            priority=Priority.HIGH,
            task_type=TaskType.TRADE_EXECUTION,
            created_at=datetime.now()
        )
        
        result = scheduler.submit_task(task)
        
        assert result == True
        assert len(scheduler.task_queue) == 1
    
    def test_queue_sorting_by_priority(self):
        """Queue is sorted by priority (lower value = higher priority)"""
        scheduler = PriorityScheduler()
        
        # Create tasks with different priorities
        low_task = Task("low", "Low", Priority.LOW, TaskType.BACKUP, datetime.now())
        high_task = Task("high", "High", Priority.HIGH, TaskType.TRADE_EXECUTION, datetime.now())
        critical_task = Task("critical", "Critical", Priority.CRITICAL, TaskType.RISK_CHECK, datetime.now())
        
        scheduler.submit_task(low_task)
        scheduler.submit_task(high_task)
        scheduler.submit_task(critical_task)
        
        # Check order: CRITICAL should be first
        next_task = scheduler.get_next_task()
        assert next_task.priority == Priority.CRITICAL
    
    def test_queue_full_rejection(self):
        """Low priority tasks rejected when queue is full"""
        scheduler = PriorityScheduler()
        scheduler.max_queue_size = 3
        
        # Fill queue
        for i in range(3):
            task = Task(f"task-{i}", f"Task {i}", Priority.LOW, TaskType.BACKUP, datetime.now())
            scheduler.submit_task(task)
        
        # Try to add another low priority task
        new_low = Task("new-low", "New Low", Priority.LOW, TaskType.BACKUP, datetime.now())
        result = scheduler.submit_task(new_low)
        
        assert result == False  # Should be rejected
    
    def test_high_priority_preempts_low(self):
        """High priority task can preempt low priority when queue full"""
        scheduler = PriorityScheduler()
        scheduler.max_queue_size = 3
        
        # Fill queue with low priority
        for i in range(3):
            task = Task(f"task-{i}", f"Task {i}", Priority.LOW, TaskType.BACKUP, datetime.now())
            scheduler.submit_task(task)
        
        # High priority should be accepted by preempting low
        high_task = Task("high", "High Priority", Priority.CRITICAL, TaskType.RISK_CHECK, datetime.now())
        result = scheduler.submit_task(high_task)
        
        assert result == True
        assert len(scheduler.task_queue) == 3  # Still at max
        assert any(t.priority == Priority.CRITICAL for t in scheduler.task_queue)
    
    def test_execute_next(self):
        """Execute next returns highest priority task"""
        scheduler = PriorityScheduler()
        
        task = Task("task-001", "Test", Priority.MEDIUM, TaskType.MARKET_DATA, datetime.now())
        scheduler.submit_task(task)
        
        executed = scheduler.execute_next()
        
        assert executed is not None
        assert executed.id == "task-001"
        assert executed.executed == True
        assert len(scheduler.task_queue) == 0
    
    def test_get_queue_status(self):
        """Queue status provides accurate statistics"""
        scheduler = PriorityScheduler()
        
        scheduler.submit_task(Task("t1", "T1", Priority.CRITICAL, TaskType.RISK_CHECK, datetime.now()))
        scheduler.submit_task(Task("t2", "T2", Priority.HIGH, TaskType.TRADE_EXECUTION, datetime.now()))
        scheduler.submit_task(Task("t3", "T3", Priority.LOW, TaskType.BACKUP, datetime.now()))
        
        status = scheduler.get_queue_status()
        
        assert status['total_tasks'] == 3
        assert status['by_priority']['CRITICAL'] == 1
        assert status['by_priority']['HIGH'] == 1
        assert status['by_priority']['LOW'] == 1


class TestCommandRouter:
    """Test command routing functionality"""
    
    def test_router_initialization(self):
        """Router initializes with scheduler"""
        scheduler = PriorityScheduler()
        router = CommandRouter(scheduler)
        
        assert router.scheduler == scheduler
        assert len(router.handlers) == 0
    
    def test_register_handler(self):
        """Handlers can be registered for task types"""
        scheduler = PriorityScheduler()
        router = CommandRouter(scheduler)
        
        def trade_handler():
            pass
        
        router.register_handler(TaskType.TRADE_EXECUTION, trade_handler)
        
        assert TaskType.TRADE_EXECUTION in router.handlers
    
    def test_route_command(self):
        """Commands are routed to scheduler if handler exists"""
        scheduler = PriorityScheduler()
        router = CommandRouter(scheduler)
        
        def trade_handler():
            pass
        
        router.register_handler(TaskType.TRADE_EXECUTION, trade_handler)
        
        task = Task(
            id="trade-001",
            name="Execute Trade",
            priority=Priority.HIGH,
            task_type=TaskType.TRADE_EXECUTION,
            created_at=datetime.now()
        )
        
        result = router.route_command(task)
        
        assert result == True
        assert len(scheduler.task_queue) == 1
    
    def test_route_unregistered_type(self):
        """Commands for unregistered types fail"""
        scheduler = PriorityScheduler()
        router = CommandRouter(scheduler)
        
        task = Task(
            id="unknown-001",
            name="Unknown",
            priority=Priority.MEDIUM,
            task_type=TaskType.LOG_ROTATION,
            created_at=datetime.now()
        )
        
        result = router.route_command(task)
        
        assert result == False


class TestPriorityMonitor:
    """Test priority monitoring functionality"""
    
    def test_monitor_initialization(self):
        """Monitor initializes with empty history"""
        monitor = PriorityMonitor()
        
        assert len(monitor.metrics_history) == 0
        assert 'critical_max_wait' in monitor.alert_thresholds
    
    def test_record_execution(self):
        """Executions are recorded with metrics"""
        monitor = PriorityMonitor()
        
        monitor.record_execution("task-001", "HIGH", 0.5, 1.0)
        
        assert len(monitor.metrics_history) == 1
        assert monitor.metrics_history[0]['task_id'] == "task-001"
        assert monitor.metrics_history[0]['priority'] == "HIGH"
    
    def test_calculate_metrics(self):
        """Metrics calculated correctly for each priority"""
        monitor = PriorityMonitor()
        
        # Add some metrics
        monitor.record_execution("t1", "CRITICAL", 0.1, 0.5)
        monitor.record_execution("t2", "CRITICAL", 0.2, 0.6)
        monitor.record_execution("t3", "HIGH", 1.0, 2.0)
        
        metrics = monitor.calculate_metrics(window_seconds=60)
        
        assert len(metrics) == 2  # CRITICAL and HIGH
        
        critical_metric = next(m for m in metrics if m.priority_level == "CRITICAL")
        assert abs(critical_metric.avg_wait_time - 0.15) < 0.001  # Floating point tolerance
        assert critical_metric.max_wait_time == 0.2
        assert critical_metric.tasks_executed == 2
    
    def test_check_alerts_critical_delay(self):
        """Alert generated when critical tasks delayed"""
        monitor = PriorityMonitor()
        monitor.alert_thresholds['critical_max_wait'] = 1.0
        
        # Record a delayed critical task
        monitor.record_execution("t1", "CRITICAL", 2.0, 0.5)  # 2s wait, exceeds 1s threshold
        
        queue_status = {'total_tasks': 50}
        alerts = monitor.check_alerts(queue_status)
        
        assert len(alerts) >= 1
        assert any("Critical tasks waiting" in alert for alert in alerts)
    
    def test_check_alerts_queue_saturation(self):
        """Alert generated when queue near saturation"""
        monitor = PriorityMonitor()
        
        queue_status = {'total_tasks': 85}  # 85% of 100
        alerts = monitor.check_alerts(queue_status)
        
        assert any("saturation" in alert.lower() for alert in alerts)
    
    def test_starvation_report(self):
        """Starvation report identifies old unexecuted tasks"""
        monitor = PriorityMonitor()
        
        # Add old task
        old_time = datetime.now() - timedelta(minutes=15)
        monitor.metrics_history.append({
            'timestamp': old_time.isoformat(),
            'task_id': 'old-task',
            'priority': 'LOW',
            'executed': False
        })
        
        report = monitor.get_starvation_report()
        
        assert len(report) >= 1
        assert any('old-task' in r for r in report)


class TestIntegration:
    """Test integration between scheduler, router, and monitor"""
    
    def test_full_priority_workflow(self):
        """Complete workflow: submit -> route -> execute -> monitor"""
        scheduler = PriorityScheduler()
        router = CommandRouter(scheduler)
        monitor = PriorityMonitor()
        
        # Register handler
        def trade_handler():
            pass
        router.register_handler(TaskType.TRADE_EXECUTION, trade_handler)
        
        # Submit high priority trade
        trade_task = Task(
            id="trade-001",
            name="Buy AAPL",
            priority=Priority.HIGH,
            task_type=TaskType.TRADE_EXECUTION,
            created_at=datetime.now()
        )
        
        # Route to scheduler
        assert router.route_command(trade_task) == True
        
        # Execute
        executed = scheduler.execute_next()
        assert executed is not None
        
        # Record in monitor
        monitor.record_execution(
            executed.id,
            executed.priority.name,
            0.1,  # wait time
            0.5   # execution time
        )
        
        # Verify monitor has record
        assert len(monitor.metrics_history) == 1
        assert monitor.metrics_history[0]['task_id'] == "trade-001"
    
    def test_preemption_scenario(self):
        """Critical task preempts ongoing low priority work"""
        scheduler = PriorityScheduler()
        scheduler.max_queue_size = 2
        
        # Fill with medium priority
        scheduler.submit_task(Task("m1", "Medium 1", Priority.MEDIUM, TaskType.MARKET_DATA, datetime.now()))
        scheduler.submit_task(Task("m2", "Medium 2", Priority.MEDIUM, TaskType.HEARTBEAT, datetime.now()))
        
        # Critical task arrives
        critical = Task("critical", "Critical Risk Check", Priority.CRITICAL, TaskType.RISK_CHECK, datetime.now())
        
        # Should trigger preemption check
        should_preempt = scheduler.preempt_low_priority(critical)
        
        assert should_preempt == True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
