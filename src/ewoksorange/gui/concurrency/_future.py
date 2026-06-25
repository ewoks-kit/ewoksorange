import weakref
from concurrent.futures import Future as _Future
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import CancellableAndAbortableExecutor
    from .base import TaskExecutionID


class TaskFuture(_Future):
    """Future associated to an ewoks Tasks that can be cancelled and / or aborted."""

    def __init__(
        self,
        task_exec_id: "TaskExecutionID",
        executor: "CancellableAndAbortableExecutor",
    ):
        super().__init__()

        self._executor = weakref.ref(executor)
        self.task_kwargs = {}
        self.task_exec_id = task_exec_id

    @property
    def executor(self) -> "CancellableAndAbortableExecutor":
        return self._executor()

    def cancel(self) -> bool:
        """
        Cancel a pending processing.

        :return: True if cancellation succeded.
        """
        if self.done():
            return False
        if not self.executor:
            return False
        self.executor._cancel_future(self)
        return super().cancel()

    def abort(self) -> bool:
        """
        Abort (if possible) an on-going processing.

        :return: True if abortion succeded.
        """
        if not self.executor:
            return False
        res = self.executor._abort_future(self)
        return res
