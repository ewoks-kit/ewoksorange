"""
Synchronous (no-thread) Ewoks widget implementation.
"""

from concurrent.futures import Future as _ConcurrentFuture
from typing import Optional

from ..concurrency.base import TaskExecutor
from ..concurrency.executor import TaskFuture
from ..concurrency.executor._EwoksCompletedWorker import (
    CompletedWorker as _CompletedWorker,
)
from .base import OWEwoksBaseWidget
from .meta import ow_build_opts


class OWEwoksWidgetNoThread(OWEwoksBaseWidget, **ow_build_opts):
    """
    Widget that creates and executes an Ewoks Task synchronously on the main thread.

    Use this for lightweight tasks that won't block the UI.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__task_executor = TaskExecutor(self.ewokstaskclass)

    def _execute_ewoks_task(
        self, propagate: bool, log_missing_inputs: bool
    ) -> Optional[TaskFuture]:
        # Both methods handle exceptions internally (ewokscore >= 4.0.1):
        # create_task() stores TaskInputError silently; execute_task() never raises.
        self.__task_executor.create_task(
            log_missing_inputs=log_missing_inputs, **self._get_task_arguments()
        )
        self.__task_executor.execute_task()

        task_exception = self.__task_executor.exception
        try:
            if propagate:
                # Always pass an explicit bool — passing None triggers a DeprecationWarning
                # (base.py:533) which becomes an error under pytest -W error.
                self.propagate_downstream(succeeded=task_exception is None)
        finally:
            self._output_changed()

        raw_future = _ConcurrentFuture()
        if task_exception is not None:
            raw_future.set_exception(task_exception)
        else:
            raw_future.set_result(self.__task_executor.output_variables)
        return TaskFuture(raw_future, _CompletedWorker())

    @property
    def task_succeeded(self) -> Optional[bool]:
        """Return True if last task succeeded, False if failed, None if never run."""
        return self.__task_executor.succeeded

    @property
    def task_done(self) -> Optional[bool]:
        """Return True if last task finished (success/failure), None if never run."""
        return self.__task_executor.done

    @property
    def task_exception(self) -> Optional[Exception]:
        """Return the exception raised during last task execution, if any."""
        return self.__task_executor.exception

    def _get_task_outputs(self) -> dict:
        """Return output variables produced by the last executed task."""
        return self.__task_executor.output_variables
