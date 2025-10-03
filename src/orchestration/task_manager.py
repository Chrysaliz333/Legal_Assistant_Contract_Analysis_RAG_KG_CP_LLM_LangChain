"""Task queue implementation for adaptive agent orchestration."""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass(order=True)
class Task:
    """Represents an actionable unit of work for an agent."""

    priority: int
    created_at: float
    task_id: str = field(compare=False)
    task_type: str = field(compare=False)
    payload: Dict[str, Any] = field(compare=False)
    depends_on: Optional[str] = field(default=None, compare=False)


class TaskManager:
    """Priority queue with dependency tracking."""

    def __init__(self) -> None:
        self._counter = itertools.count()
        self._queue: List[Task] = []
        self._in_progress: Dict[str, Task] = {}
        self._completed: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Queue operations
    # ------------------------------------------------------------------
    def enqueue(
        self,
        task_type: str,
        payload: Dict[str, Any],
        priority: int = 10,
        depends_on: Optional[str] = None,
    ) -> str:
        """Add a task to the queue and return its identifier."""

        task_id = payload.get("task_id") or f"task-{next(self._counter)}"
        task = Task(
            priority=priority,
            created_at=datetime.utcnow().timestamp(),
            task_id=task_id,
            task_type=task_type,
            payload=payload,
            depends_on=depends_on,
        )
        heapq.heappush(self._queue, task)
        return task_id

    def dequeue(self) -> Optional[Task]:
        """Return the next runnable task, skipping blocked dependencies."""

        while self._queue:
            candidate = heapq.heappop(self._queue)
            if candidate.depends_on and candidate.depends_on not in self._completed:
                # Dependency incomplete; requeue with slight penalty
                candidate.priority += 1
                heapq.heappush(self._queue, candidate)
                continue
            self._in_progress[candidate.task_id] = candidate
            return candidate
        return None

    def mark_complete(self, task_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        """Record completion data and remove from in-progress registry."""

        task = self._in_progress.pop(task_id, None)
        if not task:
            return
        self._completed[task_id] = {
            "task_type": task.task_type,
            "payload": task.payload,
            "completed_at": datetime.utcnow().isoformat(),
            "result": result or {},
        }

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------
    def pending_count(self) -> int:
        return len(self._queue)

    def in_progress(self) -> List[Task]:
        return list(self._in_progress.values())

    def completed(self) -> Dict[str, Dict[str, Any]]:
        return self._completed

