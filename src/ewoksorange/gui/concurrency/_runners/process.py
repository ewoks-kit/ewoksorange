import queue
import threading
from typing import Any
from typing import Dict
from typing import Type

from ewokscore.task import Task

from .abstract import TaskRunner


class ProcessTaskRunner(TaskRunner):
    """Picklable callable executed inside the subprocess."""

    _TRANSIENT_ABORT_ERRORS = (EOFError, BrokenPipeError, ConnectionError)
    # The manager providing the IPC objects shut down.

    def __init__(
        self,
        task_class: Type[Task],
        task_kwargs: Dict[str, Any],
        ready_event: threading.Event,
        started_queue: queue.Queue,
        abort_event: threading.Event,
        aborted_event: threading.Event,
    ):
        super().__init__(task_class, task_kwargs, abort_event)
        self._ready_event = ready_event
        self._started_queue = started_queue
        self._aborted_event = aborted_event

    def _wait_ready(self) -> None:
        self._ready_event.wait()

    def _announce_started(self, task: Task) -> None:
        self._started_queue.put("started")

    def _finalize(self, task: Task) -> None:
        try:
            if task.cancelled:
                self._aborted_event.set()
        except self._TRANSIENT_ABORT_ERRORS:
            pass
