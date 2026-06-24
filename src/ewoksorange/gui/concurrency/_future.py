from typing import TYPE_CHECKING
import weakref
from concurrent.futures import Future as _Future

if TYPE_CHECKING:
    from .base import TaskExecutionID


class TaskFuture(_Future):
    """Future associated to an ewoks Tasks that can be cancelled and / or aborted."""

    def __init__(
        self,
        task_exec_id: "TaskExecutionID",
        executor,
    ):
        super().__init__()

        self._executor = weakref.ref(executor)
        self.task_kwargs = {}
        self.task_exec_id = task_exec_id

    @property
    def executor(self):
        return self._executor()

    def cancel(self) -> bool:
        # The Future 'cancel' API only works if the start hasn't cancel yet...
        if self.done():
            return False
        if not self.executor:
            return False
        self.executor._cancel_future(self)
        return super().cancel()

    def abort(self) -> bool:
        if not self.executor:
            return False
        res = self.executor._abort_future(self)
        return res
