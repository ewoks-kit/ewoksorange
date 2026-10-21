"""
Messages between the controller of an ewoks task and the runner executing it in
another process.

Each direction has its own queue. The queue to the controller carries "about to start",
"started" and progress, so the controller receives them in the order the runner put
them. The queue to the runner carries the start decision and stop requests.
"""

import queue
from enum import Enum
from enum import auto

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

    END = auto()
    """End the reading of the queue. Put by the runner itself."""


class QueueProgress(BasePercentageProgress):
    """Picklable progress that forwards updates to the controller.

    Shares the queue to the controller with the :class:`ToController` messages.
    """

    _TRANSIENT_ERRORS = (EOFError, BrokenPipeError, ConnectionError)
    # The manager providing the queue shut down.

    def __init__(self, to_controller_queue: queue.Queue):
        """
        :param to_controller_queue: A `multiprocessing` manager queue proxy.
        """
        super().__init__()
        self._progress_queue = to_controller_queue

    def _update(self) -> None:
        """Send the current progress to the controller."""
        try:
            self._progress_queue.put(self._progress)
        except self._TRANSIENT_ERRORS:
            pass
