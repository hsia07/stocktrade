"""
Task Priority Scheduler
Round 9: Commands and Task Priority
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


class Priority(Enum):
    """Task priority levels"""
    CRITICAL = 1    # System-critical tasks
    HIGH = 2        # Trading-related tasks
    MEDIUM = 3      # Monitoring tasks
    LOW = 4         # Background maintenance


class TaskType(Enum):
    """Types of tasks"""
    TRADE_EXECUTION = "trade_execution"
    RISK_CHECK = "risk_check"
    MARKET_DATA = "market_data"
    HEARTBEAT = "heartbeat"
    LOG_ROTATION = "log_rotation"
    BACKUP = "backup"


@dataclass
class Task:
    """Represents a scheduled task"""
    id: str
    name: str
    priority: Priority
    task_type: TaskType
    created_at: datetime
    deadline: Optional[datetime] = None
    executed: bool = False
    execution_time: Optional[float] = None  # seconds


class PriorityScheduler:
    """
    Priority-based task scheduler
    Ensures critical tasks don't get blocked by background tasks
    """
    
    def __init__(self):
        self.task_queue: List[Task] = []
        self.execution_history: List[Task] = []
        self.max_queue_size = 100
    
    def submit_task(self, task: Task) -> bool:
        """
        Submit a task to the queue
        
        Returns:
            bool: True if task was accepted, False if queue is full
        """
        if len(self.task_queue) >= self.max_queue_size:
            # Reject lowest priority task if queue is full
            lowest = self._find_lowest_priority_task()
            if lowest and lowest.priority.value > task.priority.value:
                self.task_queue.remove(lowest)
            else:
                return False
        
        self.task_queue.append(task)
        self._sort_queue()
        return True
    
    def get_next_task(self) -> Optional[Task]:
        """Get the highest priority task from the queue"""
        if not self.task_queue:
            return None
        
        # Return highest priority task (sorted by priority, then deadline)
        return self.task_queue[0]
    
    def execute_next(self) -> Optional[Task]:
        """Execute the highest priority task"""
        task = self.get_next_task()
        if task:
            self.task_queue.remove(task)
            task.executed = True
            task.execution_time = 0.0  # Would be measured in real implementation
            self.execution_history.append(task)
        return task
    
    def preempt_low_priority(self, new_task: Task) -> bool:
        """
        Check if new high-priority task should preempt current execution
        
        Returns:
            bool: True if current task should be preempted
        """
        current = self.get_next_task()
        if current and new_task.priority.value < current.priority.value:
            return True
        return False
    
    def get_tasks_by_priority(self, priority: Priority) -> List[Task]:
        """Get all tasks of a specific priority level"""
        return [t for t in self.task_queue if t.priority == priority]
    
    def get_queue_status(self) -> dict:
        """Get current queue statistics"""
        status = {
            'total_tasks': len(self.task_queue),
            'by_priority': {},
            'oldest_task_age': None
        }
        
        for priority in Priority:
            count = len(self.get_tasks_by_priority(priority))
            status['by_priority'][priority.name] = count
        
        if self.task_queue:
            oldest = min(self.task_queue, key=lambda t: t.created_at)
            age = (datetime.now() - oldest.created_at).total_seconds()
            status['oldest_task_age'] = age
        
        return status
    
    def _sort_queue(self):
        """Sort queue by priority (ascending) and deadline"""
        def sort_key(task: Task):
            deadline_key = task.deadline or datetime.max
            return (task.priority.value, deadline_key)
        
        self.task_queue.sort(key=sort_key)
    
    def _find_lowest_priority_task(self) -> Optional[Task]:
        """Find the lowest priority task in the queue"""
        if not self.task_queue:
            return None
        return max(self.task_queue, key=lambda t: t.priority.value)
    
    def clear_completed(self):
        """Clear execution history"""
        self.execution_history.clear()


class CommandRouter:
    """
    Routes commands to appropriate handlers based on priority
    """
    
    def __init__(self, scheduler: PriorityScheduler):
        self.scheduler = scheduler
        self.handlers = {}
    
    def register_handler(self, task_type: TaskType, handler):
        """Register a handler for a task type"""
        self.handlers[task_type] = handler
    
    def route_command(self, task: Task) -> bool:
        """
        Route a command to its handler
        
        Returns:
            bool: True if command was routed successfully
        """
        if task.task_type in self.handlers:
            # Add to scheduler queue
            return self.scheduler.submit_task(task)
        return False
    
    def get_handler(self, task_type: TaskType):
        """Get the handler for a task type"""
        return self.handlers.get(task_type)
