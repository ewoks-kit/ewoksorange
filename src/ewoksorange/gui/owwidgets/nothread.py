"""
Synchronous (no-thread) Ewoks widget implementation.
"""

import logging
from typing import Optional

from ..concurrency.base import TaskExecutor
from .base import OWEwoksBaseWidget
from .meta import ow_build_opts

_logger = logging.getLogger(__name__)


class OWEwoksWidgetNoThread(OWEwoksBaseWidget, **ow_build_opts):
    """
    Widget that creates and executes an Ewoks Task synchronously on the main thread.

    Use this for lightweight tasks that won't block the UI.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the no-thread widget and preparer a TaskExecutor.
        """
        super().__init__(*args, **kwargs)
        self.__task_executor = TaskExecutor(self.ewokstaskclass)

    def _execute_ewoks_task(self, propagate: bool, log_missing_inputs: bool) -> None:
        """
        Create and execute the Task synchronously.

        :param propagate: Whether to propagate outputs after execution.
        :param log_missing_inputs: Whether to log missing input warnings.
        """
        self.__task_executor.create_task(
            log_missing_inputs=log_missing_inputs, **self._get_task_arguments()
        )
        try:
            self.__task_executor.execute_task()
        except Exception as e:
            _logger.error(f"task failed: {e}", exc_info=True)
        try:
            self.__post_task_exception = None
            if propagate:
                self.propagate_downstream()
        finally:
            self._output_changed()

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

    def get_task_outputs(self) -> dict:
        """Return output variables produced by the last executed task."""
        return self.__task_executor.output_variables
