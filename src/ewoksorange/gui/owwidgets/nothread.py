"""
Synchronous (no-thread) Ewoks widget implementation.
"""

from typing import Optional

from ..concurrency.executor import EwoksExecutor
from ..concurrency.executor import SubmitPolicy
from ..concurrency.executor import TaskFuture
from .base import OWEwoksBaseWidget
from .meta import ow_build_opts


class OWEwoksWidgetNoThread(OWEwoksBaseWidget, **ow_build_opts):
    """
    Widget that creates and executes an Ewoks Task synchronously on the main thread.

    Use this for lightweight tasks that won't block the UI.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__executor = EwoksExecutor(None, SubmitPolicy.ALWAYS)

        self.__last_output_variables: dict = {}
        self.__last_task_succeeded: Optional[bool] = None
        self.__last_task_done: Optional[bool] = None
        self.__last_task_exception: Optional[Exception] = None

    def _execute_ewoks_task(
        self, propagate: bool, log_missing_inputs: bool
    ) -> Optional[TaskFuture]:
        """
        Create and execute the Task synchronously.

        :param propagate: Whether to propagate outputs after execution.
        :param log_missing_inputs: Whether to log missing input warnings.
        :return: TaskFuture, or None when the execution request was rejected.
        """
        task_future = self.__executor.submit_task(
            self.ewokstaskclass, **self._get_task_arguments()
        )
        if task_future is None:
            return None

        # Submission runs (and completes) synchronously, so the result is
        # already available here rather than through the executor's signals.
        exception = task_future.exception()
        self.__last_task_exception = exception
        self.__last_task_succeeded = exception is None
        self.__last_task_done = True
        self.__last_output_variables = task_future.result() if exception is None else {}

        try:
            if propagate:
                self.propagate_downstream(succeeded=exception is None)
        finally:
            self._output_changed()

        return task_future

    @property
    def task_succeeded(self) -> Optional[bool]:
        """Return True if last task succeeded, False if failed, None if never run."""
        return self.__last_task_succeeded

    @property
    def task_done(self) -> Optional[bool]:
        """Return True if last task finished (success/failure), None if never run."""
        return self.__last_task_done

    @property
    def task_exception(self) -> Optional[Exception]:
        """Return the exception raised during last task execution, if any."""
        exc = self.__last_task_exception
        if exc is None:
            return None
        # task.execute() wraps run() exceptions as TaskExecutionError(...) from
        # the original; follow __cause__ to surface the exception the task
        # actually raised. Task construction failures (TaskInputError) have
        # no __cause__ and are returned as-is.
        return exc.__cause__ or exc

    def _get_task_outputs(self) -> dict:
        """Return output variables produced by the last executed task."""
        return self.__last_output_variables
