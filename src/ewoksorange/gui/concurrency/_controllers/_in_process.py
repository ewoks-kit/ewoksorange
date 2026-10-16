import threading
from concurrent.futures import Future
from typing import Optional

from .abstract import StartDenial
from .abstract import TaskController


class _InProcessTaskController(TaskController):
    """Shared base for a task running in this process (the calling thread
    or a worker thread)."""

    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()

    def try_start(self) -> Optional[StartDenial]:
        """Mark the task as started unless it was denied. Returns the denial."""
        return self._gate.open()

    @property
    def stop_event(self) -> threading.Event:
        return self._stop_event

    def _send_stop_request(self) -> None:
        self._stop_event.set()

    def cancel(self, future: Future) -> bool:
        if not super().cancel(future):
            return False
        # When the pool already picked up the task, the runner does not start it.
        future.cancel()
        return True
