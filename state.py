"""In-memory task state for Jovaltus plugin.

Each task records:
- task_id: unique string ID
- project_dir: absolute path to the git repo
- start_hash: git commit hash when the task began
- created_at: Unix timestamp
"""

import threading
import time
from typing import Optional

_tasks: dict[str, dict] = {}
_lock = threading.Lock()
_counter = 0


def create_task(project_dir: str, start_hash: str) -> str:
    """Create a new task record and return its task_id."""
    global _counter
    with _lock:
        _counter += 1
        task_id = f"jt-{int(time.time() * 1000)}-{_counter}"
        _tasks[task_id] = {
            "task_id": task_id,
            "project_dir": project_dir,
            "start_hash": start_hash,
            "created_at": time.time(),
        }
    return task_id


def get_task(task_id: str) -> Optional[dict]:
    """Look up a task by ID. Returns None if not found."""
    with _lock:
        return _tasks.get(task_id)


def task_count() -> int:
    """Return the number of active tasks."""
    with _lock:
        return len(_tasks)


def clear_tasks() -> int:
    """Remove all tasks. Returns the number removed."""
    with _lock:
        n = len(_tasks)
        _tasks.clear()
        return n


def update_task_start_hash(task_id: str, new_start_hash: str) -> bool:
    """Update the start_hash of an existing task.

    Useful for re-verifying against a different baseline.
    Returns True if the task was updated, False if not found.
    """
    with _lock:
        task = _tasks.get(task_id)
        if task is None:
            return False
        task["start_hash"] = new_start_hash
        return True
