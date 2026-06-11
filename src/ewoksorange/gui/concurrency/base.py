import logging
import uuid
from typing import Optional
from typing import Type
from typing import TypeAlias

from ewokscore import TaskWithProgress
from ewokscore.task import Task
from ewokscore.task import TaskInputError

from ._future import TaskFuture

_logger = logging.getLogger(__name__)

TaskExecutionID: TypeAlias = str
from ._future import ExecutorFutureHandler


class TaskExecutor(ExecutorFutureHandler):
    """Create and execute an Ewoks task"""

    def __init__(self, ewokstaskclass: Type[Task]) -> None:
        self.__ewokstaskclass = ewokstaskclass
        self.__task = None
        self.__task_init_exception = None

    def create_task(self, log_missing_inputs: bool = False, **kwargs) -> None:
        if not issubclass(self.__ewokstaskclass, TaskWithProgress):
            kwargs.pop("progress", None)
        self.__task = None
        self.__task_init_exception = None
        try:
            self.__task = self.__ewokstaskclass(**kwargs)
        except TaskInputError as e:
            self.__task_init_exception = e
            if log_missing_inputs:
                _logger.error(f"task initialization failed: {e}", exc_info=True)
            else:
                _logger.info(f"task initialization failed: {e}")

    def execute_task(self) -> TaskFuture:
        """
        Execute the task and return a tuple indicating success of the submission and the execution ID.
        """
        future = TaskFuture(
            task_exec_id=str(
                uuid.uuid4()
            ),  # Use a dummy TaskExecutionID since we couldn't create the task)
            executor=self,
        )
        if not self.has_task:
            # if no task defined this mean that initialization has failed.
            future.set_exception(RuntimeError("Task not defined."))
            return future

        try:
            self.__task.execute()
        except Exception as e:
            _logger.error(f"task failed: {e}", exc_info=True)
            future.set_exception(exception=e)
        else:
            future.set_result(self.__task.output_values)
        return future

    @property
    def has_task(self) -> bool:
        return self.__task is not None

    @property
    def succeeded(self) -> Optional[bool]:
        """Returns `None` when the task was not or could not be instantiated"""
        if self.__task is None:
            return None
        return self.__task.succeeded

    @property
    def done(self) -> Optional[bool]:
        """Returns `None` when the task was not or could not be instantiated"""
        if self.__task is None:
            return None
        return self.__task.done

    @property
    def exception(self) -> Optional[Exception]:
        """The instantiation exception, the execution exception or `None`"""
        if self.__task_init_exception is not None:
            return self.__task_init_exception
        if self.__task is None:
            return None
        return self.__task.exception

    @property
    def output_variables(self) -> Optional[dict]:
        if self.__task is None:
            return dict()
        return self.__task.output_variables

    @property
    def current_task(self) -> Optional[Task]:
        return self.__task

    def cancel_task(self, task_exec_id: TaskExecutionID) -> None:
        pass

    def cancel_all_tasks(self) -> None:
        pass

    def _cancel_future(self, future: TaskFuture):
        pass
