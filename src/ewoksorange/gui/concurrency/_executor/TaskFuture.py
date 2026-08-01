from concurrent.futures import Future

from ._EwoksTaskHandle import EwoksTaskHandle as _EwoksTaskHandle


class TaskFuture:
    """Wraps a concurrent.futures.Future with ewoks-specific abort support."""

    def __init__(self, raw_future: Future, worker: _EwoksTaskHandle):
        self._future = raw_future
        self._worker = worker

    def cancel(self) -> bool:
        """Prevent execution if the task has not started (native future cancel)."""
        return self._future.cancel()

    def abort(self) -> bool:
        """Abort a running ewoks task. Returns True if the task was reached and cancelled."""
        return self._worker.abort()

    def aborted(self) -> bool:
        """Return True if the underlying ewoks task was aborted."""
        return self._worker.aborted()

    def cancelled(self) -> bool:
        return self._future.cancelled()

    def running(self) -> bool:
        return self._future.running()

    def done(self) -> bool:
        return self._future.done()

    def result(self, timeout=None):
        return self._future.result(timeout=timeout)

    def exception(self, timeout=None):
        return self._future.exception(timeout=timeout)

    def add_done_callback(self, fn):
        self._future.add_done_callback(fn)
