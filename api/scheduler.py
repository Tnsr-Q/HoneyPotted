```python
"""
Background task scheduler for Quantum Deception Nexus.
Handles periodic tasks like cleanup, statistics, and monitoring.
"""

import threading
import time
import logging
from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import sqlite3
import json

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class ScheduledTask:
    """Represents a scheduled task."""
    name: str
    func: Callable
    interval: int  # seconds
    last_run: Optional[float] = None
    enabled: bool = True
    args: tuple = ()
    kwargs: dict = None
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}

class TaskScheduler:
    """Background task scheduler."""
    
    def __init__(self, db_path: str = "quantum_nexus.db"):
        self.db_path = db_path
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self._init_database()
        
    def _init_database(self):
        """Initialize scheduler database tables."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    func_name TEXT NOT NULL,
                    interval INTEGER NOT NULL,
                    last_run TIMESTAMP,
                    enabled BOOLEAN DEFAULT 1,
                    args TEXT,
                    kwargs TEXT
                )
            ''')
            
            # Create task logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Scheduler database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize scheduler database: {e}")
            
    def add_task(self, name: str, func: Callable, interval: int, 
                 args: tuple = (), kwargs: dict = None, enabled: bool = True):
        """Add a new scheduled task."""
        if kwargs is None:
            kwargs = {}
            
        task = ScheduledTask(
            name=name,
            func=func,
            interval=interval,
            args=args,
            kwargs=kwargs,
            enabled=enabled
        )
        
        self.tasks[name] = task
        logger.info(f"Added scheduled task: {name} (interval: {interval}s)")
        
        # Save to database
        self._save_task_to_db(task)
        
    def remove_task(self, name: str):
        """Remove a scheduled task."""
        if name in self.tasks:
            del self.tasks[name]
            self._remove_task_from_db(name)
            logger.info(f"Removed scheduled task: {name}")
            
    def enable_task(self, name: str):
        """Enable a scheduled task."""
        if name in self.tasks:
            self.tasks[name].enabled = True
            self._update_task_in_db(self.tasks[name])
            logger.info(f"Enabled scheduled task: {name}")
            
    def disable_task(self, name: str):
        """Disable a scheduled task."""
        if name in self.tasks:
            self.tasks[name].enabled = False
            self._update_task_in_db(self.tasks[name])
            logger.info(f"Disabled scheduled task: {name}")
            
    def _save_task_to_db(self, task: ScheduledTask):
        """Save task to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO scheduled_tasks 
                (name, func_name, interval, last_run, enabled, args, kwargs)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                task.name,
                task.func.__name__,
                task.interval,
                datetime.fromtimestamp(task.last_run) if task.last_run else None,
                task.enabled,
                json.dumps(task.args),
                json.dumps(task.kwargs)
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save task {task.name} to database: {e}")
            
    def _update_task_in_db(self, task: ScheduledTask):
        """Update task in database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE scheduled_tasks 
                SET interval = ?, last_run = ?, enabled = ?, args = ?, kwargs = ?
                WHERE name = ?
            ''', (
                task.interval,
                datetime.fromtimestamp(task.last_run) if task.last_run else None,
                task.enabled,
                json.dumps(task.args),
                json.dumps(task.kwargs),
                task.name
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to update task {task.name} in database: {e}")
            
    def _remove_task_from_db(self, name: str):
        """Remove task from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM scheduled_tasks WHERE name = ?', (name,))
            cursor.execute('DELETE FROM task_logs WHERE task_name = ?', (name,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to remove task {name} from database: {e}")
            
    def load_tasks_from_db(self):
        """Load tasks from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM scheduled_tasks')
            rows = cursor.fetchall()
            
            for row in rows:
                task = ScheduledTask(
                    name=row['name'],
                    func=lambda: None,  # Placeholder, actual function needs to be resolved
                    interval=row['interval'],
                    last_run=row['last_run'],
                    enabled=bool(row['enabled']),
                    args=json.loads(row['args']) if row['args'] else (),
                    kwargs=json.loads(row['kwargs']) if row['kwargs'] else {}
                )
                self.tasks[row['name']] = task
                
            conn.close()
            logger.info(f"Loaded {len(rows)} tasks from database")
        except Exception as e:
            logger.error(f"Failed to load tasks from database: {e}")
            
    def start(self):
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
            
        self.running = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("Scheduler started")
        
    def stop(self):
        """Stop the scheduler."""
        if not self.running:
            logger.warning("Scheduler is not running")
            return
            
        self.running = False
        self.stop_event.set()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            
        logger.info("Scheduler stopped")
        
    def _run(self):
        """Main scheduler loop."""
        while self.running and not self.stop_event.is_set():
            try:
                current_time = time.time()
                
                # Execute due tasks
                for task in self.tasks.values():
                    if not task.enabled:
                        continue
                        
                    if (task.last_run is None or 
                        current_time - task.last_run >= task.interval):
                        self._execute_task(task, current_time)
                        
                # Sleep for a short interval
                self.stop_event.wait(1)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                self.stop_event.wait(5)  # Wait longer on error
                
    def _execute_task(self, task: ScheduledTask, current_time: float):
        """Execute a scheduled task."""
        logger.info(f"Executing task: {task.name}")
        
        try:
            start_time = time.time()
            
            # Execute the task
            result = task.func(*task.args, **task.kwargs)
            
            execution_time = time.time() - start_time
            
            # Update task metadata
            task.last_run = current_time
            
            # Log success
            self._log_task_result(task.name, "SUCCESS", 
                                f"Executed in {execution_time:.2f}s")
                                
            logger.info(f"Task {task.name} completed successfully in {execution_time:.2f}s")
            
        except Exception as e:
            # Log failure
            self._log_task_result(task.name, "ERROR", str(e))
            logger.error(f"Task {task.name} failed: {e}")
            
        finally:
            # Update task in database
            self._update_task_in_db(task)
            
    def _log_task_result(self, task_name: str, status: str, message: str):
        """Log task execution result."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO task_logs (task_name, status, message)
                VALUES (?, ?, ?)
            ''', (task_name, status, message))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log task result for {task_name}: {e}")
            
    def get_task_status(self) -> Dict[str, Any]:
        """Get status of all tasks."""
        status = {}
        current_time = time.time()
        
        for name, task in self.tasks.items():
            status[name] = {
                'enabled': task.enabled,
                'interval': task.interval,
                'last_run': task.last_run,
                'next_run': task.last_run + task.interval if task.last_run else None,
                'overdue': (
                    task.enabled and 
                    task.last_run and 
                    current_time - task.last_run > task.interval
                )
            }
            
        return status
        
    def get_task_logs(self, task_name: str = None, limit: int = 100) -> list:
        """Get task execution logs."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if task_name:
                cursor.execute('''
                    SELECT * FROM task_logs 
                    WHERE task_name = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (task_name, limit))
            else:
                cursor.execute('''
                    SELECT * FROM task_logs 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                
            logs = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return logs
        except Exception as e:
            logger.error(f"Failed to get task logs: {e}")
            return []

# Example scheduled tasks
def database_cleanup():
    """Clean up old database records."""
    logger.info("Running database cleanup task")
    # Implementation would go here

def aggregate_statistics():
    """Aggregate system statistics."""
    logger.info("Running statistics aggregation task")
    # Implementation would go here

def monitor_system_health():
    """Monitor system health."""
    logger.info("Running system health monitoring task")
    # Implementation would go here

def generate_reports():
    """Generate automated reports."""
    logger.info("Running report generation task")
    # Implementation would go here

def backup_data():
    """Backup system data."""
    logger.info("Running data backup task")
    # Implementation would go here

# Global scheduler instance
scheduler = TaskScheduler()

# Export for module usage
__all__ = ["TaskScheduler", "scheduler", "ScheduledTask"]
```