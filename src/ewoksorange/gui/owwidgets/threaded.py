"""
Threaded Ewoks widget implementations.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Optional

from ..concurrency._future import TaskFuture
from ..concurrency.base import TaskExecutionID
from ..concurrency.queued import TaskExecutorQueue
from ..concurrency.threaded import MultiThreadedTaskExecutor
from ..concurrency.threaded import ThreadedTaskExecutor
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

    def cancel_task(self, task_exec_id: TaskExecutionID) -> None:
        """Subclasses should implement cancellation logic for their specific executors."""
        raise NotImplementedError("Base class")


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
        self._current_task_exec_id = ""

    def _execute_ewoks_task(
        self, propagate: bool, log_missing_inputs: bool
    ) -> TaskFuture:
        """
        Prepare and start the background thread if idle.

        :param propagate: Whether to propagate outputs after execution.
        :param log_missing_inputs: Whether to log missing input warnings.
        :return: Future of the task execution.
        """
        future = self.__task_executor.create_task(
            log_missing_inputs=log_missing_inputs, **self._get_task_arguments()
        )
        future.task_kwargs = self._get_task_arguments()
        if self.__task_executor.has_task:
            with self._ewoks_task_start_context():
                self.__propagate = propagate
                self.__task_executor.start()
                self._current_task_exec_id = future.task_exec_id
        else:
            err = "Task undefined. Executor not correctly initialized."
            future.set_exception(RuntimeError(err))
            _logger.error(err)
            self.__propagate = propagate
            self.__task_executor.finished.emit()
            self._current_task_exec_id = ""
        return future

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

    def _get_task_outputs(self) -> dict:
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

    def _cancel_running_task(self):
        self.__task_executor._cancel_running_task()

    def cancel_task(self, task_exec_id: TaskExecutionID) -> None:
        if task_exec_id == self._current_task_exec_id:
            self._cancel_running_task()


class OWEwoksWidgetOneThreadPerRun(_OWEwoksThreadedBaseWidget, **ow_build_opts):
    """
    Creates a new ThreadedTaskExecutor for every task run so multiple runs can overlap.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the multi-thread task executor.
        """
        super().__init__(*args, **kwargs)
        self.__task_executor = MultiThreadedTaskExecutor(
            ewokstaskclass=self.ewokstaskclass
        )

    def _execute_ewoks_task(
        self, propagate: bool, log_missing_inputs: bool
    ) -> TaskFuture:
        """
        Submit a task to the multi-thread executor.

        :param propagate: Whether to propagate outputs after execution.
        :param log_missing_inputs: Whether to log missing input warnings.
        :return: Future of the task execution.
        """
        with self._ewoks_task_start_context():
            return self.__task_executor.execute_task(
                _callbacks=(
                    lambda task_executor: self._ewoks_task_finished_callback(
                        task_executor, propagate
                    ),
                ),
                log_missing_inputs=log_missing_inputs,
                **self._get_task_arguments(),
            )

    def _ewoks_task_finished_callback(
        self, task_executor: ThreadedTaskExecutor, propagate: bool
    ):
        """
        Slot invoked when a per-run executor finishes; stores its outputs and optionally propagates.
        """
        with self._ewoks_task_finished_context():
            self.__post_task_exception = None
            if propagate:
                self.propagate_downstream(succeeded=task_executor.succeeded)

    def _cleanup_task_executor(self):
        """Stop all tracked per-run executors on widget cleanup."""
        self.__task_executor.stop()
        self.__task_executor = None

    @property
    def task_succeeded(self) -> Optional[bool]:
        return self.__task_executor.task_succeeded

    @property
    def task_done(self) -> Optional[bool]:
        return self.__task_executor.task_done

    @property
    def task_exception(self) -> Optional[Exception]:
        return self.__task_executor.task_exception

    def _get_task_outputs(self) -> dict:
        """Return the last finished task's outputs."""
        return self.__task_executor.output_variables

    def _cancel_future(self, future: TaskFuture) -> None:
        """In the case of 'one thread per run' we can only abort."""
        return False

    def _abort_future(self, future: TaskFuture) -> None:
        return self.__task_executor._abort_future(future)


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

    def _execute_ewoks_task(
        self, propagate: bool, log_missing_inputs: bool
    ) -> TaskFuture:
        """
        Queue the task for later execution in FIFO order.

        :param propagate: Whether to propagate outputs after execution.
        :param log_missing_inputs: Whether to log missing input warnings.
        :return: Future of the task execution.
        """

        def callback():
            self._ewoks_task_finished_callback(propagate)

        with self._ewoks_task_start_context():
            future = self.__task_executor_queue.add(
                _callbacks=(callback,),
                _log_missing_inputs=log_missing_inputs,
                **self._get_task_arguments(),
            )
        return future

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

    def _cancel_running_task(self):
        """Cancel the currently running task in the queue, if any."""
        self.__task_executor_queue._cancel_running_task()

    def cancel_task(self, task_exec_id):
        """
        Cancel a specific task by ID, whether it's currently running or still in the queue.

        :param task_exec_id: The ID of the task to cancel.
        :return: True if the task was found and cancellation was initiated, False otherwise.
        """
        self.__task_executor_queue.cancel_task(task_exec_id)
