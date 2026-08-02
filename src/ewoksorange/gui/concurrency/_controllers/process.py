import logging
import threading
from multiprocessing.synchronize import Event
from queue import Queue
from typing import Callable
from typing import Optional

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
        self._started_handled = threading.Event()
        self._on_started_thread: Optional[threading.Thread] = None

    def watch_started(self, on_started: Callable[[], None]) -> None:
        """Call `on_started` once the child process reports it has started."""

        def _relay():
            try:
                if self._started_queue.get(timeout=300) == "started":
                    on_started()
            except Exception:
                _logger.debug("started relay failed", exc_info=True)
            finally:
                self._started_handled.set()

        self._on_started_thread = threading.Thread(target=_relay, daemon=True)
        self._on_started_thread.start()

    def wait_started(self, timeout: Optional[float] = None) -> None:
        """Wait for `on_started` to be finished."""

        if not self._started_handled.wait(timeout=timeout):
            # Release the relay thread
            try:
                self._started_queue.put("__stop__")
            except Exception:
                _logger.debug("failed to stop the started relay", exc_info=True)

        if self._on_started_thread is not None:
            self._on_started_thread.join(timeout=5.0)
            if self._on_started_thread.is_alive():
                _logger.debug("started relay thread did not terminate in time")

    def abort(self) -> bool:
        self._abort_event.set()
        return True

    def aborted(self) -> bool:
        return self._aborted_event.is_set()
