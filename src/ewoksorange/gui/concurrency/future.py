from __future__ import annotations

from concurrent.futures import CancelledError
from concurrent.futures import Future
from typing import Any
from typing import Callable
from typing import Collection
from typing import Dict
from typing import Optional

from ewokscore.variable import VariableContainer

from . import _controllers


class TaskStoppedError(RuntimeError):
    """Raised by :meth:`TaskFuture.result` when a stop request prevented the task from starting."""


class TaskAbortedError(RuntimeError):
    """Raised by :meth:`TaskFuture.result` when the task was aborted or killed."""


class TaskFuture:
    """Future of an ewoks task submitted to an `EwoksExecutor`.

    Ways to prevent or end the execution, from mild to forceful:

    1. :meth:`cancel` (do not run): has no effect on a running task.
    2. :meth:`request_stop` (cooperative): the running task is asked to stop and decides
       whether and how (see `Task.stop_requested` and `Task._on_stop_requested`).
    3. :meth:`abort` (forced, with cleanup): the running task is interrupted like Ctrl-C,
       also when it ignores stop requests. Subprocess only.
    4. :meth:`kill` (forced, no cleanup): the subprocess running the task is terminated,
       also when the task does not return to the Python interpreter. Subprocess only.

    Each of them prevents a queued task from starting. Only the first one that reaches
    a queued task has an effect. None of them has an effect on a finished task.

    :meth:`cancelled`, :meth:`stop_requested`, :meth:`aborted` and :meth:`killed`
    report which of these happened.
    """

    def __init__(
        self,
        raw_future: Future[VariableContainer],
        controller: _controllers.TaskController,
        on_stop_requested: Optional[Callable[[], None]] = None,
    ):
        self._future = raw_future
        self._controller = controller
        self._on_stop_requested = on_stop_requested

    def cancel(self) -> bool:
        """Prevent a queued task from starting. Has no effect once the task started.

        The result raises `CancelledError`.

        :return: True if this prevented the task from starting.
        """
        return self._controller.cancel(self._future)

    def request_stop(self) -> bool:
        """Ask the ewoks task to stop (cooperative).

        Supported for all backends. A queued task never starts and the result raises
        :class:`TaskStoppedError`. A running task decides whether and how to stop and
        the result is whatever the task returns or raises.

        :return: True if this prevented the task from starting or reached the running task.
        """
        if self.done():
            return False
        requested = self._controller.request_stop()
        if requested and not self.done() and self._on_stop_requested is not None:
            on_stop_requested, self._on_stop_requested = self._on_stop_requested, None
            on_stop_requested()
        return requested

    def stop_requested(self) -> bool:
        """Return True if :meth:`request_stop` prevented the start or reached the ewoks task."""
        return self._controller.stop_requested()

    def abort(self) -> bool:
        """Interrupt the ewoks task like Ctrl-C (forced, with cleanup).

        Only supported for tasks running in a subprocess. A queued task never starts.
        A running task is interrupted, also when it ignores stop requests. The task can
        clean up and the subprocess survives. It only takes effect when the task returns
        to the Python interpreter: use :meth:`kill` otherwise. The result raises
        :class:`TaskAbortedError`.

        :return: True if this prevented the task from starting or was sent to the running task.
        """
        if self.done():
            return False
        return self._controller.abort()

    def kill(self) -> bool:
        """Terminate the subprocess running the ewoks task (forced, no cleanup).

        Only supported for tasks running in a subprocess. A queued task never starts.
        Unlike :meth:`abort`, this also works when a running task does not return to the
        Python interpreter. The task cannot clean up and the pool replaces the subprocess.
        The result raises :class:`TaskAbortedError`.

        :return: True if this prevented the task from starting or killed the running task.
        """
        return self._controller.kill(self._future)

    def aborted(self) -> bool:
        """Return True if :meth:`abort` prevented the start or interrupted the ewoks task."""
        return self._controller.aborted(self._future)

    def killed(self) -> bool:
        """Return True if :meth:`kill` prevented the start or terminated the ewoks task."""
        return self._controller.killed()

    def cancelled(self) -> bool:
        """Return True if :meth:`cancel` prevented the execution."""
        return self._controller.cancelled(self._future)

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
        try:
            result = self._future.result(timeout=timeout)
        except CancelledError:
            if self._controller.killed():
                raise _killed_error() from None
            raise
        if self.cancelled():
            raise CancelledError()
        return result

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
        return self.exception(timeout=timeout) is None

    def exception(self, timeout: Optional[float] = None) -> Optional[BaseException]:
        """The exception raised by the ewoks task execution.

        :param timeout: Maximum number of seconds to wait for the future to complete, `None` to wait forever.
        :raises TimeoutError: The task did not finish in time.
        :raises CancelledError: The task was cancelled before it started.
        :return: The exception or `None` when the task succeeded.
        """
        try:
            exception = self._future.exception(timeout=timeout)
        except CancelledError:
            if self._controller.killed():
                return _killed_error()
            raise
        if exception is None and self.cancelled():
            raise CancelledError()
        return exception

    def task_exception(
        self, timeout: Optional[float] = None
    ) -> Optional[BaseException]:
        """The original exception causing the ewoks task execution exception.

        :param timeout: Maximum number of seconds to wait for the future to complete, `None` to wait forever.
        :raises TimeoutError: The task did not finish in time.
        :raises CancelledError: The task was cancelled before it started.
        :return: The exception or `None` when the task succeeded.
        """
        exc = self.exception(timeout=timeout)
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


def _killed_error() -> TaskAbortedError:
    return TaskAbortedError("The task was killed")
