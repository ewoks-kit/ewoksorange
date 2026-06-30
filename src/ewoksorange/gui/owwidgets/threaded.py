"""
Threaded Ewoks widget implementations.
"""

from __future__ import annotations

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


class _OWEwoksThreadedBaseWidget(OWEwoksBaseWidget, **ow_build_opts):
    """Common threaded behavior: progress handling and cleanup hooks."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__taskProgress = QProgress()
        self.__taskProgress.sigProgressChanged.connect(self.__onProgressChanged)

    def onDeleteWidget(self):
        self.__taskProgress.sigProgressChanged.disconnect(self.__onProgressChanged)
        self._cleanup_task_executor()
        super().onDeleteWidget()

    def _cleanup_task_executor(self):
        raise NotImplementedError("Base class")

    @contextmanager
    def _ewoks_task_start_context(self):
        """Context manager that initialises progress before a task starts."""
        try:
            self.__ewoks_task_init()
            yield
        except Exception:
            self.__ewoks_task_finished()
            raise

    @contextmanager
    def _ewoks_task_finished_context(self):
        """Context manager that finalises progress after a task ends."""
        try:
            yield
        finally:
            self.__ewoks_task_finished()

    def __ewoks_task_init(self):
        self.progressBarInit()

    def __ewoks_task_finished(self):
        self.progressBarFinished()
        self._output_changed()

    def _get_task_arguments(self):
        adict = super()._get_task_arguments()
        adict["progress"] = self.__taskProgress
        return adict

    def __onProgressChanged(self, progress: int):
        self.progressBarSet(float(progress))


class _OWEwoksExecutorWidget(_OWEwoksThreadedBaseWidget, **ow_build_opts):
    """Base for all EwoksExecutor-backed widgets."""

    _MAX_WORKERS: Optional[int] = 1
    _SUBMIT_POLICY: SubmitPolicy = SubmitPolicy.ALWAYS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__executor = EwoksExecutor(
            ThreadPoolExecutor(max_workers=self._MAX_WORKERS),
            self._SUBMIT_POLICY,
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
        try:
            if propagate:
                self.propagate_downstream()
        finally:
            self._output_changed()

    def __on_failed(self, task_future: TaskFuture, exc: Exception) -> None:
        propagate = self.__propagate_by_future.pop(task_future, False)
        self.__last_output_variables = {}
        self.__last_task_succeeded = False
        self.__last_task_done = True
        self.__last_task_exception = exc
        self.progressBarFinished()
        try:
            if propagate:
                self.propagate_downstream()
        finally:
            self._output_changed()

    @property
    def task_executor(self) -> EwoksExecutor:
        """The underlying :class:`EwoksExecutor`."""
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


class OWEwoksWidgetOneThread(_OWEwoksExecutorWidget, **ow_build_opts):
    """Single background thread; submissions while busy are dropped."""

    _MAX_WORKERS: Optional[int] = 1
    _SUBMIT_POLICY = SubmitPolicy.DROP_IF_BUSY


class OWEwoksWidgetOneThreadPerRun(_OWEwoksExecutorWidget, **ow_build_opts):
    """Submits each task to a shared thread pool; multiple runs may overlap."""

    _MAX_WORKERS = None


class OWEwoksWidgetWithTaskStack(_OWEwoksExecutorWidget, **ow_build_opts):
    """FIFO queue: tasks are queued and run sequentially in a single thread."""

    _MAX_WORKERS: Optional[int] = 1

    @property
    def task_executor_queue(self) -> EwoksExecutor:
        """Alias for :attr:`task_executor` kept for backward compatibility."""
        return self.task_executor
