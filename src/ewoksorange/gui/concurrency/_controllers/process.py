import logging
import threading
from multiprocessing.synchronize import Event
from queue import Queue
from typing import Callable
from typing import Optional

from .. import _progress
from .abstract import TaskController

_logger = logging.getLogger(__name__)


class ProcessTaskController(TaskController):
    """Controls a task running in another process.

    Communication with the child process happens through multiprocessing
    Event/Queue proxies. The child reports "about to start", "started" and
    progress through a single queue, relayed by a single thread, so the
    callbacks are called in the order the child emitted them.
    """

    def __init__(
        self,
        abort_event: Event,
        aborted_event: Event,
        events_queue: Queue,
    ):
        self._abort_event = abort_event
        self._aborted_event = aborted_event
        self._events_queue = events_queue
        self._relay_thread: Optional[threading.Thread] = None

    def watch(
        self,
        on_about_to_start: Callable[[], None],
        on_started: Callable[[], None],
        on_progress: Optional[Callable[[float], None]] = None,
    ) -> None:
        """Relay the events reported by the child process to the callbacks."""

        def _relay():
            while True:
                try:
                    # No timeout: `stop_watching` always ends the relay.
                    message = self._events_queue.get()
                except Exception:
                    _logger.debug("events relay failed", exc_info=True)
                    return
                if message == _progress.STOP:
                    return
                try:
                    if message == _progress.ABOUT_TO_START:
                        on_about_to_start()
                    elif message == _progress.STARTED:
                        on_started()
                    elif on_progress is not None:
                        on_progress(message)
                except Exception:
                    _logger.debug("events callback failed", exc_info=True)

        self._relay_thread = threading.Thread(target=_relay, daemon=True)
        self._relay_thread.start()

    def stop_watching(self) -> None:
        """Wait for all events to be relayed, then stop the relay.

        The child puts every event before returning its result, while the
        sentinel below is only put once the parent sees the task finished (or
        cancelled). Manager queues are FIFO, so draining up to the sentinel
        delivers all of them.
        """
        if self._relay_thread is None:
            return

        try:
            self._events_queue.put(_progress.STOP)
        except Exception:
            _logger.debug("failed to stop the events relay", exc_info=True)

        self._relay_thread.join(timeout=5.0)
        if self._relay_thread.is_alive():
            _logger.debug("events relay thread did not terminate in time")

    def abort(self) -> bool:
        self._abort_event.set()
        return True

    def aborted(self) -> bool:
        return self._aborted_event.is_set()
