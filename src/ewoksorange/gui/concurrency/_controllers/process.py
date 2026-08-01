import logging
import threading
from multiprocessing.synchronize import Event
from queue import Queue
from typing import Callable

from .abstract import TaskController

_logger = logging.getLogger(__name__)


class ProcessTaskController(TaskController):
    """Controls a task running in another process.

    Communication with the child process happens through multiprocessing
    Event/Queue proxies.
    """

    def __init__(
        self,
        abort_event: Event,
        aborted_event: Event,
        started_queue: Queue,
    ):
        self._abort_event = abort_event
        self._aborted_event = aborted_event
        self._started_queue = started_queue

    def watch_started(self, on_started: Callable[[], None]) -> None:
        """Call `on_started` once the child process reports it has started."""

        def _relay():
            try:
                if self._started_queue.get(timeout=300) == "started":
                    on_started()
            except Exception:
                _logger.debug("started relay failed", exc_info=True)

        threading.Thread(target=_relay, daemon=True).start()

    def abort(self) -> bool:
        self._abort_event.set()
        return True

    def aborted(self) -> bool:
        return self._aborted_event.is_set()
