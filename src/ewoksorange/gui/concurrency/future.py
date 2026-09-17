from __future__ import annotations

from concurrent.futures import Future
from typing import Any
from typing import Callable
from typing import Collection
from typing import Dict
from typing import Optional

from ewokscore.variable import VariableContainer

from . import _controllers


class TaskFuture:
    """Wraps a concurrent.futures.Future with ewoks-specific abort support."""

    def __init__(
        self,
        raw_future: Future[VariableContainer],
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

    def result(self, timeout: Optional[float] = None) -> VariableContainer:
        """The output variables of the ewoks task.

        :param timeout: Maximum number of seconds to wait for the future to complete, `None` to wait forever.
        :raises TimeoutError: The task did not finish in time.
        :raises CancelledError: The task was cancelled before it started.
        :raises Exception: Whatever the task raised.
        :return: An immutable mapping of output name to
                 :class:`~ewokscore.variable.Variable`.
        """
        return self._future.result(timeout=timeout)

    def output_values(
        self, timeout: Optional[float] = None, exclude: Collection[str] = ()
    ) -> Dict[str, Any]:
        """The output values of the ewoks task.

        :param timeout: Maximum number of seconds to wait for the future to complete, `None` to wait forever.
        :param exclude: Output names to leave out.
        :raises TimeoutError: The task did not finish in time.
        :raises CancelledError: The task was cancelled before it started.
        :raises Exception: Whatever the task raised.
        :return: A mapping of output name to value, `MISSING_DATA` for outputs
                 the task did not set.
        """
        return {
            name: var.value
            for name, var in self.result(timeout=timeout).items()
            if name not in exclude
        }

    def succeeded(self, timeout: Optional[float] = None) -> bool:
        """Whether the ewoks task execution finished without raising.

        :param timeout: Maximum number of seconds to wait for the future to complete, `None` to wait forever.
        :raises TimeoutError: The task did not finish in time.
        :raises CancelledError: The task was cancelled before it started.
        """
        return self._future.exception(timeout=timeout) is None

    def exception(self, timeout: Optional[float] = None) -> Optional[BaseException]:
        """The exception raised by the ewoks task execution.

        :param timeout: Maximum number of seconds to wait for the future to complete, `None` to wait forever.
        :raises TimeoutError: The task did not finish in time.
        :raises CancelledError: The task was cancelled before it started.
        :return: The exception or `None` when the task succeeded.
        """
        return self._future.exception(timeout=timeout)

    def task_exception(
        self, timeout: Optional[float] = None
    ) -> Optional[BaseException]:
        """The original exception causing the ewoks task execution exception.

        :param timeout: Maximum number of seconds to wait for the future to complete, `None` to wait forever.
        :raises TimeoutError: The task did not finish in time.
        :raises CancelledError: The task was cancelled before it started.
        :return: The exception or `None` when the task succeeded.
        """
        exc = self._future.exception(timeout=timeout)
        if exc is None:
            return None
        # task.execute() wraps run() exceptions as TaskExecutionError(...) from
        # the original. Task construction failures (TaskInputError) have
        # no __cause__ and are returned as-is.
        return exc.__cause__ or exc

    def add_done_callback(self, fn: Callable[[Future[VariableContainer]], Any]) -> None:
        """
        :param fn: Called with the wrapped future, not with this object.
        """
        self._future.add_done_callback(fn)
