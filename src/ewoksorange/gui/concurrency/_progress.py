"""
Ewoks task progress across a process boundary.
"""

import queue

from ewokscore.progress import BasePercentageProgress

PROGRESS_STOP = "__stop__"
"""Sentinel put on the queue by the parent process to stop the relay."""


class QueueProgress(BasePercentageProgress):
    """Picklable progress that forwards updates to the parent process."""

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
