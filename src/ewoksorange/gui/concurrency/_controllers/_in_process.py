import threading
from threading import Lock

from ewokscore.task import Task

from .abstract import TaskController


class _InProcessTaskController(TaskController):
    """Shared base for a task running in this process (the calling thread
    or a worker thread)."""

    def __init__(self):
        self._task = None
        self._abort_event = threading.Event()
        self._lock = Lock()

    def set_task(self, task: Task) -> None:
        with self._lock:
            self._task = task

    @property
    def abort_event(self) -> threading.Event:
        return self._abort_event

    def abort(self) -> bool:
        self._abort_event.set()
        with self._lock:
            return self._task is not None

    def aborted(self) -> bool:
        with self._lock:
            task = self._task

        return task is not None and task.cancelled
