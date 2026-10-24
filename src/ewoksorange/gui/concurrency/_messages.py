"""
Messages between the controller of an ewoks task and the runner executing it in
another process.

Each direction has its own queue. The queue to the controller carries "about to start",
"started" and progress, so the controller receives them in the order the runner put
them. The queue to the runner carries the start decision, stop requests and aborts.
"""

import queue
import threading
from enum import Enum
from enum import auto
from typing import Optional

from ewokscore.progress import BasePercentageProgress


class ToController(Enum):
    """Messages on the queue to the controller, next to the progress values."""

    ABOUT_TO_START = auto()
    """The runner is about to create the task and waits for a
    :attr:`ToRunner.START` or a `StartDenial`."""

    STARTED = auto()
    """The runner created the task."""

    END = auto()
    """End the reading of the queue. Put by the controller itself."""


class ToRunner(Enum):
    """Messages on the queue to the runner."""

    START = auto()
    """Reply to :attr:`ToController.ABOUT_TO_START`: the task may start. Otherwise
    the reply is a `StartDenial`."""

    REQUEST_STOP = auto()
    """Request the running task to stop."""

    ABORT = auto()
    """Interrupt the running task."""

    END = auto()
    """End the reading of the queue. Put by the runner itself."""


_STOP_SENDING = object()

_MAX_PENDING = 100
# The task waits for the sender thread when it reports progress faster than it is sent.


class QueueProgress(BasePercentageProgress):
    """Picklable progress that forwards updates to the controller.

    Shares the queue to the controller with the :class:`ToController` messages.
    Between :meth:`start_sending` and :meth:`stop_sending`, a sender thread forwards
    the updates.
    """

    _TRANSIENT_ERRORS = (EOFError, BrokenPipeError, ConnectionError)
    # The manager providing the queue shut down.

    def __init__(self, to_controller_queue: queue.Queue):
        """
        :param to_controller_queue: A `multiprocessing` manager queue proxy.
        """
        super().__init__()
        self._progress_queue = to_controller_queue
        self._pending: Optional[queue.Queue] = None
        self._sender: Optional[threading.Thread] = None
        self._discard = False

    def start_sending(self) -> None:
        """Start the thread that sends the progress values to the controller."""
        self._pending = queue.Queue(maxsize=_MAX_PENDING)
        self._sender = threading.Thread(
            target=self._send, args=(self._pending,), daemon=True
        )
        self._sender.start()

    def stop_sending(self, discard: bool = False) -> None:
        """Send the remaining progress values, or drop them, and stop the sender thread."""
        if self._sender is None:
            return
        self._discard = discard
        self._pending.put(_STOP_SENDING)
        self._sender.join()
        self._pending = None
        self._sender = None

    def _update(self) -> None:
        """Send the current progress, through the sender thread when it runs."""
        if self._pending is not None:
            # The sender thread runs. Not sent from here: an abort interrupts the task
            # thread, which would leave the manager connection of that thread out of sync.
            self._pending.put(self._progress)
        else:
            self._put(self._progress)

    def _send(self, pending: queue.Queue) -> None:
        """Send the queued progress values until :meth:`stop_sending`."""
        while True:
            value = pending.get()
            if value is _STOP_SENDING:
                return
            if not self._discard:
                self._put(value)

    def _put(self, value: float) -> None:
        try:
            self._progress_queue.put(value)
        except self._TRANSIENT_ERRORS:
            pass
