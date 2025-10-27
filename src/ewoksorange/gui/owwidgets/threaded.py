"""
Threaded Ewoks widget implementations.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Dict
from typing import Optional
from typing import Tuple

from ...orange_version import ORANGE_VERSION
from ..concurrency.queued import TaskExecutorQueue
from ..concurrency.threaded import ThreadedTaskExecutor
from ..qt_utils.progress import QProgress
from .base import OWEwoksBaseWidget
from .meta import ow_build_opts

_logger = logging.getLogger(__name__)

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    has_progress_bar = True
elif ORANGE_VERSION == ORANGE_VERSION.latest_orange:
    has_progress_bar = True
else:
    has_progress_bar = False


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
        if has_progress_bar:
            self.__taskProgress = QProgress()
            self.__taskProgress.sigProgressChanged.connect(self.progressBarSet)
        else:
            self.__taskProgress = None

    def onDeleteWidget(self):
        """
        Clean up progress connections and task executors on widget deletion.
        """
        if has_progress_bar:
            self.__taskProgress.sigProgressChanged.disconnect(self.progressBarSet)
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
        if has_progress_bar:
            self.progressBarInit()

    def __ewoks_task_finished(self):
        """Internal: finalize progress UI and notify output change."""
        if has_progress_bar:
            self.progressBarFinished()
        self._output_changed()

    def _get_task_arguments(self):
        """
        Include the progress object into the task arguments.
        """
        adict = super()._get_task_arguments()
        adict["progress"] = self.__taskProgress
        return adict


class OWEwoksWidgetOneThread(_OWEwoksThreadedBaseWidget, **ow_build_opts):
    """
    Single persistent background thread for task execution.

    A second execution request while the thread is running is refused.
    """

    def __init__(self, *args, **kwargs):
        """
        Create the threaded task executor and connect finished signal.
        """
        super().__init__(*args, **kwargs)
        self.__task_executor = ThreadedTaskExecutor(ewokstaskclass=self.ewokstaskclass)
        self.__task_executor.finished.connect(self._ewoks_task_finished_callback)
        self.__propagate = None

    def _execute_ewoks_task(self, propagate: bool, log_missing_inputs: bool) -> None:
        """
        Prepare and start the background thread if idle.

        :param propagate: Whether to propagate outputs after execution.
        :param log_missing_inputs: Whether to log missing input warnings.
        """
        if self.__task_executor.isRunning():
            _logger.error("A processing is already ongoing")
            return
        self.__task_executor.create_task(
            log_missing_inputs=log_missing_inputs, **self._get_task_arguments()
        )
        if self.__task_executor.has_task:
            with self._ewoks_task_start_context():
                self.__propagate = propagate
                self.__task_executor.start()
        else:
            self.__propagate = propagate
            self.__task_executor.finished.emit()

    @property
    def task_executor(self):
        """Access the underlying ThreadedTaskExecutor instance."""
        return self.__task_executor

    @property
    def task_succeeded(self) -> Optional[bool]:
        return self.__task_executor.succeeded

    @property
    def task_done(self) -> Optional[bool]:
        return self.__task_executor.done

    @property
    def task_exception(self) -> Optional[Exception]:
        return self.__task_executor.exception

    def get_task_outputs(self) -> dict:
        """Return outputs from the running/last thread task executor."""
        return self.__task_executor.output_variables

    def _ewoks_task_finished_callback(self):
        """
        Internal slot called when the thread executor finishes.

        Finalizes progress context and propagates outputs if requested.
        """
        with self._ewoks_task_finished_context():
            self.__post_task_exception = None
            if self.__propagate:
                self.propagate_downstream()

    def _cleanup_task_executor(self):
        """Disconnect signals and stop the thread on cleanup."""
        self.__task_executor.finished.disconnect(self._ewoks_task_finished_callback)
        self.__task_executor.stop()
        self.__task_executor = None

    def cancel_running_task(self):
        """Request cancellation of a running task."""
        self.__task_executor.cancel_running_task()


class OWEwoksWidgetOneThreadPerRun(_OWEwoksThreadedBaseWidget, **ow_build_opts):
    """
    Creates a new ThreadedTaskExecutor for every task run so multiple runs can overlap.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize per-run executor storage.
        """
        super().__init__(*args, **kwargs)
        self.__task_executors: Dict[int, Tuple[ThreadedTaskExecutor, bool]] = dict()
        self.__last_output_variables = dict()
        self.__last_task_succeeded = None
        self.__last_task_done = None
        self.__last_task_exception = None

    def _execute_ewoks_task(self, propagate: bool, log_missing_inputs: bool) -> None:
        """
        Create a fresh ThreadedTaskExecutor, register it, and start it if it has work.

        :param propagate: Whether to propagate outputs after execution.
        :param log_missing_inputs: Whether to log missing input warnings.
        """
        task_executor = ThreadedTaskExecutor(ewokstaskclass=self.ewokstaskclass)
        task_executor.create_task(
            log_missing_inputs=log_missing_inputs, **self._get_task_arguments()
        )
        with self.__init_task_executor(task_executor, propagate):
            if task_executor.has_task:
                with self._ewoks_task_start_context():
                    task_executor.start()
            else:
                task_executor.finished.emit()

    @contextmanager
    def __init_task_executor(self, task_executor, propagate: bool):
        """
        Register a task executor and connect its finished callback for safe cleanup.

        :param task_executor: The ThreadedTaskExecutor instance.
        :param propagate: Propagate flag to store with the executor.
        """
        task_executor.finished.connect(self._ewoks_task_finished_callback)
        self.__add_task_executor(task_executor, propagate)
        try:
            yield
        except Exception:
            task_executor.finished.disconnect(self._ewoks_task_finished_callback)
            self.__remove_task_executor(task_executor)
            raise

    def __disconnect_all_task_executors(self):
        """Disconnect all connected finished signals from tracked executors."""
        for task_executor, _ in self.__task_executors.values():
            if task_executor.receivers(task_executor.finished) > 0:
                task_executor.finished.disconnect(self._ewoks_task_finished_callback)

    def _ewoks_task_finished_callback(self):
        """
        Slot invoked when a per-run executor finishes; stores its outputs and optionally propagates.
        """
        with self._ewoks_task_finished_context():
            task_executor = None
            try:
                task_executor = self.sender()
                self.__last_output_variables = task_executor.output_variables
                self.__last_task_succeeded = task_executor.succeeded
                self.__last_task_done = task_executor.done
                self.__last_task_exception = task_executor.exception
                self.__post_task_exception = None
                propagate = self.__is_task_executor_propagated(task_executor)
                if propagate:
                    self.propagate_downstream(succeeded=task_executor.succeeded)
            finally:
                self.__remove_task_executor(task_executor)

    def _cleanup_task_executor(self):
        """Disconnect and quit all tracked executors on widget cleanup."""
        self.__disconnect_all_task_executors()
        for task_executor, _ in self.__task_executors.values():
            task_executor.quit()
        self.__task_executors.clear()

    def __add_task_executor(self, task_executor, propagate: bool):
        """Internal: register a new task executor with its propagate flag."""
        self.__task_executors[id(task_executor)] = task_executor, propagate

    def __remove_task_executor(self, task_executor: ThreadedTaskExecutor):
        """Internal: unregister a task executor and disconnect its signals."""
        if task_executor is None:
            return
        if task_executor.receivers(task_executor.finished) > 0:
            task_executor.finished.disconnect(self._ewoks_task_finished_callback)
        self.__task_executors.pop(id(task_executor), None)

    def __is_task_executor_propagated(self, task_executor) -> bool:
        """Return whether the given executor was registered to propagate."""
        return self.__task_executors.get(id(task_executor), (None, False))[1]

    @property
    def task_succeeded(self) -> Optional[bool]:
        return self.__last_task_succeeded

    @property
    def task_done(self) -> Optional[bool]:
        return self.__last_task_done

    @property
    def task_exception(self) -> Optional[Exception]:
        return self.__last_task_exception

    def get_task_outputs(self) -> dict:
        """Return the last finished task's outputs."""
        return self.__last_output_variables


class OWEwoksWidgetWithTaskStack(_OWEwoksThreadedBaseWidget, **ow_build_opts):
    """
    FIFO queue-based task executor wrapper.

    New task requests are placed into a queue and processed sequentially.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the FIFO TaskExecutorQueue.
        """
        super().__init__(*args, **kwargs)
        self.__task_executor_queue = TaskExecutorQueue(
            ewokstaskclass=self.ewokstaskclass
        )
        self.__last_output_variables = dict()
        self.__last_task_succeeded = None
        self.__last_task_done = None
        self.__last_task_exception = None

    @property
    def task_executor_queue(self):
        """Access the underlying TaskExecutorQueue."""
        return self.__task_executor_queue

    def _execute_ewoks_task(self, propagate: bool, log_missing_inputs: bool) -> None:
        """
        Queue the task for later execution in FIFO order.

        :param propagate: Whether to propagate outputs after execution.
        :param log_missing_inputs: Whether to log missing input warnings.
        """

        def callback():
            self._ewoks_task_finished_callback(propagate)

        with self._ewoks_task_start_context():
            self.__task_executor_queue.add(
                _callbacks=(callback,),
                _log_missing_inputs=log_missing_inputs,
                **self._get_task_arguments(),
            )

    @property
    def task_succeeded(self) -> Optional[bool]:
        return self.__last_task_succeeded

    @property
    def task_done(self) -> Optional[bool]:
        return self.__last_task_done

    @property
    def task_exception(self) -> Optional[Exception]:
        return self.__last_task_exception

    def get_task_outputs(self) -> dict:
        """Return outputs from the last completed queued task."""
        return self.__last_output_variables

    def _cleanup_task_executor(self):
        """Stop and clear the task queue on cleanup."""
        self.__task_executor_queue.stop()
        self.__task_executor_queue = None

    def _ewoks_task_finished_callback(self, propagate: bool):
        """
        Callback invoked by the queue when a task completes.

        Stores the task results and propagates downstream if requested.
        """
        with self._ewoks_task_finished_context():
            task_executor = self.sender()
            self.__last_output_variables = task_executor.output_variables
            self.__last_task_succeeded = task_executor.succeeded
            self.__last_task_done = task_executor.done
            self.__last_task_exception = task_executor.exception
            self.__post_task_exception = None
            if propagate:
                self.propagate_downstream()

    def cancel_running_task(self):
        """Cancel the currently running task in the queue, if any."""
        self.__task_executor_queue.cancel_running_task()
