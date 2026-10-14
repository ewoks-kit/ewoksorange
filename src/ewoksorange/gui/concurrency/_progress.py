"""
Messages between the parent process and the child process executing an ewoks task.

Each direction has its own queue. The queue to the parent carries "about to start",
"started" and progress, so the parent receives them in the order the child process
put them. The queue to the child carries the start decision, stop requests and aborts.
"""

import queue
from enum import Enum
from enum import auto

from ewokscore.progress import BasePercentageProgress


class ToParent(Enum):
    """Messages on the queue to the parent process, next to the progress values."""

    ABOUT_TO_START = auto()
    """The child process is about to create the task and waits for a
    :attr:`ToChild.START` or a `StartDenial`."""

    STARTED = auto()
    """The child process created the task."""

    END = auto()
    """End the reading of the queue. Put by the parent process itself."""


class ToChild(Enum):
    """Messages on the queue to the child process."""

    START = auto()
    """Reply to :attr:`ToParent.ABOUT_TO_START`: the task may start. Otherwise
    the reply is a `StartDenial`."""

    REQUEST_STOP = auto()
    """Request the running task to stop."""

    ABORT = auto()
    """Interrupt the running task."""

    END = auto()
    """End the reading of the queue. Put by the child process itself."""


class QueueProgress(BasePercentageProgress):
    """Picklable progress that forwards updates to the parent process.

    Shares the queue to the parent with the :class:`ToParent` messages.
    """

    _TRANSIENT_ERRORS = (EOFError, BrokenPipeError, ConnectionError)
    # The manager providing the queue shut down.

    def __init__(self, to_parent_queue: queue.Queue):
        """
        :param to_parent_queue: A `multiprocessing` manager queue proxy.
        """
        super().__init__()
        self._progress_queue = to_parent_queue

    def _update(self) -> None:
        """Send the current progress to the parent process."""
        try:
            self._progress_queue.put(self._progress)
        except self._TRANSIENT_ERRORS:
            pass
