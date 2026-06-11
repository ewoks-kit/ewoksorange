import logging
import weakref
from concurrent.futures import Future as _Future
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import TaskExecutionID

_logger = logging.getLogger(__name__)


class ExecutorFutureHandler:
    """Define internal API to cancel a future."""

    def _cancel_future(self, future: TaskFuture) -> None:
        raise NotImplementedError("Base class")


class TaskFuture(_Future):
    """Implementation of Future for tasks and 'ExecutorFutureHandler'"""

    def __init__(
        self, task_exec_id: TaskExecutionID, executor: ExecutorFutureHandler, **kwargs
    ):
        super().__init__()
        if not isinstance(executor, ExecutorFutureHandler):
            raise TypeError

        self._executor = weakref.ref(executor)
        self.task_kwargs = {}
        self.task_exec_id = task_exec_id

    @property
    def executor(self) -> ExecutorFutureHandler | None:
        return self._executor()

    def cancel(self) -> bool:
        if self.done():
            return False
        if self.executor:
            self.executor._cancel_future(self)

        return super().cancel()
