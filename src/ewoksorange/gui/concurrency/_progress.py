"""
Ewoks task events (about to start, started, progress) across a process boundary.

They all travel through a single queue, so the parent receives them in the
order the child process emitted them.
"""

import queue

from ewokscore.progress import BasePercentageProgress

ABOUT_TO_START = "__about_to_start__"
"""Put on the queue by the child process right before creating the task."""

STARTED = "__started__"
"""Put on the queue by the child process once the task is created."""

STOP = "__stop__"
"""Sentinel put on the queue by the parent process to stop the relay."""


class QueueProgress(BasePercentageProgress):
    """Picklable progress that forwards updates to the parent process.

    Shares its queue with the other task events (see :data:`STARTED`).
    """

    _TRANSIENT_ERRORS = (EOFError, BrokenPipeError, ConnectionError)
    # The manager providing the queue shut down.

    def __init__(self, progress_queue: queue.Queue):
        """
        :param progress_queue: A `multiprocessing` manager queue proxy.
        """
        super().__init__()
        self._progress_queue = progress_queue

    def _update(self) -> None:
        """Send the current progress to the parent process."""
        try:
            self._progress_queue.put(self._progress)
        except self._TRANSIENT_ERRORS:
            pass
