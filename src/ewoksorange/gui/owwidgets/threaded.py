"""
Threaded Ewoks widget implementations.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Dict
from typing import Optional

from ..concurrency.executor import EwoksExecutor
from ..concurrency.executor import SubmitPolicy
from ..concurrency.executor import TaskFuture
from ..qt_utils.progress import QProgress
from .base import OWEwoksBaseWidget
from .meta import ow_build_opts

_logger = logging.getLogger(__name__)


class _OWEwoksThreadedBaseWidget(OWEwoksBaseWidget, **ow_build_opts):
    """
    Common threaded behavior: progress handling and cleanup hooks.

    Subclasses should use _ewoks_task_start_context and _ewoks_task_finished_context
    around task start/finish logic to ensure proper progress bar handling.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize threaded base internals, including optional progress object.
        """
        super().__init__(*args, **kwargs)
        self.__taskProgress = QProgress()
        self.__taskProgress.sigProgressChanged.connect(self.__onProgressChanged)

    def onDeleteWidget(self):
        """
        Clean up progress connections and task executors on widget deletion.
        """
        self.__taskProgress.sigProgressChanged.disconnect(self.__onProgressChanged)
        self._cleanup_task_executor()
        super().onDeleteWidget()

    def _cleanup_task_executor(self):
        """
        Subclasses must implement cleanup of their specific task executors/threads.
        """
        raise NotImplementedError("Base class")

    @contextmanager
    def _ewoks_task_start_context(self):
        """
        Context manager invoked when a task is about to start.

        Initializes progress bar and yields control to caller.
        """
        try:
            self.__ewoks_task_init()
            yield
        except Exception:
            self.__ewoks_task_finished()
            raise

    @contextmanager
    def _ewoks_task_finished_context(self):
        """
        Context manager invoked when a task has finished.

        Ensures finalization and output-change handling.
        """
        try:
            yield
        finally:
            self.__ewoks_task_finished()

    def __ewoks_task_init(self):
        """Internal: initialize progress UI if available."""
        self.progressBarInit()

    def __ewoks_task_finished(self):
        """Internal: finalize progress UI and notify output change."""
        self.progressBarFinished()
        self._output_changed()

    def _get_task_arguments(self):
        """
        Include the progress object into the task arguments.
        """
        adict = super()._get_task_arguments()
        adict["progress"] = self.__taskProgress
        return adict

    def __onProgressChanged(self, progress: int):
        self.progressBarSet(float(progress))


class OWEwoksWidgetOneThread(_OWEwoksThreadedBaseWidget, **ow_build_opts):
    """
    Single background thread for task execution.

    Submissions while a task is running are dropped (DROP_IF_BUSY).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__executor = EwoksExecutor(
            ThreadPoolExecutor(max_workers=1), SubmitPolicy.DROP_IF_BUSY
        )
        self.__executor.started.connect(self.__on_started)
        self.__executor.succeeded.connect(self.__on_succeeded)
        self.__executor.failed.connect(self.__on_failed)
        self.__propagate: Optional[bool] = None
        self.__current_task_future: Optional[TaskFuture] = None
        self.__last_output_variables: dict = {}
        self.__last_task_succeeded: Optional[bool] = None
        self.__last_task_done: Optional[bool] = None
        self.__last_task_exception: Optional[Exception] = None

    def _execute_ewoks_task(
        self, propagate: bool, log_missing_inputs: bool
    ) -> Optional[TaskFuture]:
        task_future = self.__executor.submit_task(
            self.ewokstaskclass, **self._get_task_arguments()
        )
        if task_future is None:
            _logger.error("A processing is already ongoing")
            return None
        self.__propagate = propagate
        return task_future

    def __on_started(self, task_future: TaskFuture) -> None:
        self.__current_task_future = task_future
        self.progressBarInit()

    def __on_succeeded(self, task_future: TaskFuture, result: dict) -> None:
        self.__last_output_variables = result
        self.__last_task_succeeded = True
        self.__last_task_done = True
        self.__last_task_exception = None
        self.progressBarFinished()
        if self.__propagate:
            self.propagate_downstream()
        self._output_changed()

    def __on_failed(self, task_future: TaskFuture, exc: Exception) -> None:
        self.__last_output_variables = {}
        self.__last_task_succeeded = False
        self.__last_task_done = True
        self.__last_task_exception = exc
        self.progressBarFinished()
        if self.__propagate:
            self.propagate_downstream()
        self._output_changed()

    @property
    def task_executor(self) -> EwoksExecutor:
        """Access the underlying EwoksExecutor."""
        return self.__executor

    @property
    def task_succeeded(self) -> Optional[bool]:
        return self.__last_task_succeeded

    @property
    def task_done(self) -> Optional[bool]:
        return self.__last_task_done

    @property
    def task_exception(self) -> Optional[Exception]:
        return self.__last_task_exception

    def _get_task_outputs(self) -> dict:
        return self.__last_output_variables

    def _cleanup_task_executor(self) -> None:
        self.__executor.shutdown(wait=False)
        self.__executor = None

    def cancel_running_task(self) -> None:
        """Abort the currently running task."""
        if self.__current_task_future is not None:
            self.__current_task_future.abort()


class OWEwoksWidgetOneThreadPerRun(_OWEwoksThreadedBaseWidget, **ow_build_opts):
    """
    Submits each task run to a shared thread pool; multiple runs can overlap.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__executor = EwoksExecutor(
            ThreadPoolExecutor(max_workers=None), SubmitPolicy.ALWAYS
        )
        self.__executor.started.connect(self.__on_started)
        self.__executor.succeeded.connect(self.__on_succeeded)
        self.__executor.failed.connect(self.__on_failed)
        self.__propagate_by_future: Dict[TaskFuture, bool] = {}
        self.__last_output_variables: dict = {}
        self.__last_task_succeeded: Optional[bool] = None
        self.__last_task_done: Optional[bool] = None
        self.__last_task_exception: Optional[Exception] = None

    def _execute_ewoks_task(
        self, propagate: bool, log_missing_inputs: bool
    ) -> Optional[TaskFuture]:
        task_future = self.__executor.submit_task(
            self.ewokstaskclass, **self._get_task_arguments()
        )
        if task_future is not None:
            self.__propagate_by_future[task_future] = propagate
        return task_future

    def __on_started(self, task_future: TaskFuture) -> None:
        self.progressBarInit()

    def __on_succeeded(self, task_future: TaskFuture, result: dict) -> None:
        propagate = self.__propagate_by_future.pop(task_future, False)
        self.__last_output_variables = result
        self.__last_task_succeeded = True
        self.__last_task_done = True
        self.__last_task_exception = None
        self.progressBarFinished()
        if propagate:
            self.propagate_downstream(succeeded=True)
        self._output_changed()

    def __on_failed(self, task_future: TaskFuture, exc: Exception) -> None:
        propagate = self.__propagate_by_future.pop(task_future, False)
        self.__last_output_variables = {}
        self.__last_task_succeeded = False
        self.__last_task_done = True
        self.__last_task_exception = exc
        self.progressBarFinished()
        if propagate:
            self.propagate_downstream(succeeded=False)
        self._output_changed()

    @property
    def task_succeeded(self) -> Optional[bool]:
        return self.__last_task_succeeded

    @property
    def task_done(self) -> Optional[bool]:
        return self.__last_task_done

    @property
    def task_exception(self) -> Optional[Exception]:
        return self.__last_task_exception

    def _get_task_outputs(self) -> dict:
        return self.__last_output_variables

    def _cleanup_task_executor(self) -> None:
        self.__executor.shutdown(wait=False)
        self.__executor = None


class OWEwoksWidgetWithTaskStack(_OWEwoksThreadedBaseWidget, **ow_build_opts):
    """
    FIFO queue-based task executor wrapper.

    New task requests are placed into a queue and processed sequentially
    by a single background thread (ALWAYS policy, max_workers=1).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__executor = EwoksExecutor(
            ThreadPoolExecutor(max_workers=1), SubmitPolicy.ALWAYS
        )
        self.__executor.started.connect(self.__on_started)
        self.__executor.succeeded.connect(self.__on_succeeded)
        self.__executor.failed.connect(self.__on_failed)
        self.__propagate_by_future: Dict[TaskFuture, bool] = {}
        self.__current_task_future: Optional[TaskFuture] = None
        self.__last_output_variables: dict = {}
        self.__last_task_succeeded: Optional[bool] = None
        self.__last_task_done: Optional[bool] = None
        self.__last_task_exception: Optional[Exception] = None

    @property
    def task_executor_queue(self) -> EwoksExecutor:
        """Access the underlying EwoksExecutor."""
        return self.__executor

    def _execute_ewoks_task(
        self, propagate: bool, log_missing_inputs: bool
    ) -> Optional[TaskFuture]:
        task_future = self.__executor.submit_task(
            self.ewokstaskclass, **self._get_task_arguments()
        )
        if task_future is not None:
            self.__propagate_by_future[task_future] = propagate
        return task_future

    def __on_started(self, task_future: TaskFuture) -> None:
        self.__current_task_future = task_future
        self.progressBarInit()

    def __on_succeeded(self, task_future: TaskFuture, result: dict) -> None:
        propagate = self.__propagate_by_future.pop(task_future, False)
        self.__last_output_variables = result
        self.__last_task_succeeded = True
        self.__last_task_done = True
        self.__last_task_exception = None
        self.progressBarFinished()
        if propagate:
            self.propagate_downstream()
        self._output_changed()

    def __on_failed(self, task_future: TaskFuture, exc: Exception) -> None:
        propagate = self.__propagate_by_future.pop(task_future, False)
        self.__last_output_variables = {}
        self.__last_task_succeeded = False
        self.__last_task_done = True
        self.__last_task_exception = exc
        self.progressBarFinished()
        if propagate:
            self.propagate_downstream()
        self._output_changed()

    @property
    def task_succeeded(self) -> Optional[bool]:
        return self.__last_task_succeeded

    @property
    def task_done(self) -> Optional[bool]:
        return self.__last_task_done

    @property
    def task_exception(self) -> Optional[Exception]:
        return self.__last_task_exception

    def _get_task_outputs(self) -> dict:
        return self.__last_output_variables

    def _cleanup_task_executor(self) -> None:
        self.__executor.shutdown(wait=False)
        self.__executor = None

    def cancel_running_task(self) -> None:
        """Abort the currently running task."""
        if self.__current_task_future is not None:
            self.__current_task_future.abort()
