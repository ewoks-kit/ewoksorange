import logging
from concurrent.futures import Future as _Future
import weakref
from .base import TaskExecutionID

_logger = logging.getLogger(__name__)


class ExecutorFutureHandler:
    """Class allowing handling of 'TaskFuture'"""

    def cancel_task(self, task_exec_id: TaskExecutionID) -> None:
        raise NotImplementedError("Base class")


class TaskFuture(_Future):
    """Implementation of Future for tasks and 'ExecutorFutureHandler'"""

    def __init__(self, task_exec_id: str, executor: ExecutorFutureHandler, **kwargs):
        super().__init__()

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
            return self.executor._cancel_future(self)
        # this should never happen but safer to log this us case
        _logger.error("executor has been deleted. Unable to cancel.")
        return False
