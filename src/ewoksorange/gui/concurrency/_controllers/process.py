import logging
import threading
from queue import Queue
from typing import Callable
from typing import Optional

from .._messages import ToController
from .._messages import ToRunner
from .abstract import TaskController

_logger = logging.getLogger(__name__)


class ProcessTaskController(TaskController):
    """Controls a task running in another process.

    Communication with the runner in the other process happens through two
    multiprocessing queue proxies, one per direction. The runner reports "about to
    start", "started" and progress through the queue to the controller, relayed by a
    single thread, so the callbacks are called in the order the runner put them. On
    "about to start", the runner waits for the controller to allow the start through
    the queue to the runner, which then carries the stop requests.
    """

    def __init__(self, to_controller_queue: Queue, to_runner_queue: Queue):
        super().__init__()
        self._to_controller_queue = to_controller_queue
        self._to_runner_queue = to_runner_queue
        # The start decision must be the first message to the runner.
        self._to_runner_lock = threading.Lock()
        self._relay_thread: Optional[threading.Thread] = None

    def watch(
        self,
        on_about_to_start: Callable[[], None],
        on_started: Callable[[], None],
        on_progress: Optional[Callable[[float], None]] = None,
    ) -> None:
        """Relay the messages of the runner to the callbacks.

        Also decides whether the runner may start the task, so that a
        denied task never starts.
        """

        def _relay():
            while True:
                try:
                    # No timeout: `stop_watching` always ends the relay.
                    message = self._to_controller_queue.get()
                except Exception:
                    _logger.debug("events relay failed", exc_info=True)
                    return
                if message is ToController.END:
                    return
                try:
                    if message is ToController.ABOUT_TO_START:
                        self._allow_start(on_about_to_start)
                    elif message is ToController.STARTED:
                        on_started()
                    elif on_progress is not None:
                        on_progress(message)
                except Exception:
                    _logger.debug("events callback failed", exc_info=True)

        self._relay_thread = threading.Thread(target=_relay, daemon=True)
        self._relay_thread.start()

    def _allow_start(self, on_about_to_start: Callable[[], None]) -> None:
        """Reply to the runner whether it may start the task, and call
        `on_about_to_start` when allowed."""
        with self._to_runner_lock:
            denial = self._gate.open()
            # The runner waits for the reply.
            self._to_runner_queue.put(ToRunner.START if denial is None else denial)
        # Still before "started": the relay handles the events in order.
        if denial is None:
            on_about_to_start()

    def stop_watching(self) -> None:
        """Wait for all events to be relayed, then stop the relay.

        The runner puts every event before returning its result, while the
        sentinel below is only put once the controller sees the task finished (or
        cancelled). Manager queues are FIFO, so draining up to the sentinel
        delivers all of them.
        """
        # Guard in case never watched. Should never happen.
        if self._relay_thread is None:
            return

        try:
            self._to_controller_queue.put(ToController.END)
        except Exception:
            _logger.debug("failed to stop the events relay", exc_info=True)

        self._relay_thread.join(timeout=5.0)
        if self._relay_thread.is_alive():
            _logger.debug("events relay thread did not terminate in time")

    def _send_stop_request(self) -> None:
        with self._to_runner_lock:
            self._to_runner_queue.put(ToRunner.REQUEST_STOP)
