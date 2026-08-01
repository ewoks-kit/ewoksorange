from concurrent.futures import Future

from . import _controllers


class TaskFuture:
    """Wraps a concurrent.futures.Future with ewoks-specific abort support."""

    def __init__(
        self,
        raw_future: Future,
        controller: _controllers.TaskController,
    ):
        self._future = raw_future
        self._controller = controller

    def cancel(self) -> bool:
        """Prevent execution if the task has not started.

        This is the native Future cancellation mechanism. It only works while
        the task is still waiting in the executor queue.
        """
        return self._future.cancel()

    def abort(self) -> bool:
        """Abort a running ewoks task.

        This delegates to the execution controller. Depending on the execution
        backend, this may communicate with another thread, process, or do
        nothing for already-completed tasks.
        """
        return self._controller.abort()

    def aborted(self) -> bool:
        """Return True if the ewoks task was aborted."""
        return self._controller.aborted()

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
