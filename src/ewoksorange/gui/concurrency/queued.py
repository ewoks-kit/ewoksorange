from __future__ import annotations

import concurrent.futures
import uuid
import warnings
from collections import deque
from concurrent.futures import Future
from typing import Deque
from typing import Dict
from typing import Iterable

from AnyQt.QtCore import QObject
from AnyQt.QtCore import pyqtSignal as Signal

from ..qt_utils.signals import block_signals
from ._future import ExecutorFutureHandler
from ._future import TaskFuture
from .base import TaskExecutionID
from .threaded import ThreadedTaskExecutor


class TaskExecutorQueue(QObject, ExecutorFutureHandler):
    """
    Processing Queue with a First In, First Out behavior.

    When a task is added, it is put in a queue and executed when the current task is finished.
    `add()` method returns a task identifier that can be used to cancel the task before it starts.
    """

    sigComputationStarted = Signal()
    """Signal emitted when a computation is started"""
    sigComputationEnded = Signal()
    """Signal emitted when a computation is ended"""

    def __init__(self, ewokstaskclass):
        super().__init__()
        self._task_queue: Deque[Future] = deque()
        """Queue storing task IDs in FIFO order"""
        self._task_futures: Dict[str:Future] = {}
        """Dictionary mapping task IDs to their keyword arguments"""
        self._current_task_future: TaskFuture | None = None
        self._task_executor: ThreadedTaskExecutor = _ThreadedTaskExecutor(
            ewokstaskclass=ewokstaskclass
        )
        self._task_executor.finished.connect(self._process_ended)

    @property
    def is_available(self) -> bool:
        return self._current_task_future is None

    def add(self, **kwargs) -> TaskFuture:
        """Add a task `ewokstaskclass` execution request

        :return: Task identifier (UUID) that can be used to cancel the task
        """
        task_exec_id = str(uuid.uuid4())
        future = TaskFuture(task_exec_id=task_exec_id, executor=self)

        future.task_kwargs = kwargs

        self._task_futures[task_exec_id] = future
        self._task_queue.append(future)

        if self.is_available:
            self._process_next()

        return future

    def _process_next(self):
        if not self._task_queue:
            return

        self._current_task_future = self._task_queue.popleft()
        task_kwargs = self._current_task_future.task_kwargs
        self._current_task_future.set_running_or_notify_cancel()

        self._task_executor.create_task(**task_kwargs)
        if self._task_executor.has_task:
            self.sigComputationStarted.emit()
            self._task_executor.start()
        else:
            self._task_executor.finished.emit()

    def _process_ended(self):
        self._process_ended_direct(self.sender())

    def _process_ended_direct(self, task_executor: "_ThreadedTaskExecutor"):
        if self._task_executor.current_task and (
            not self._task_executor.current_task.cancelled
        ):
            self._current_task_future.set_result(
                self._task_executor.current_task.get_output_values()
            )

        for callback in task_executor.callbacks:
            callback()
        self.sigComputationEnded.emit()
        self._current_task_future = None
        if self.is_available:
            self._process_next()

    def cancel_running_task(self, wait=True):
        warnings.warn(
            f"'cancel_running_task' has been deprecated. Processing cancellation can now be done by the Future created during the task submission",
            DeprecationWarning,
            stacklevel=2,
        )
        # To check: at the moment the closest would be something like:
        current_future = self._current_task_future
        if not current_future:
            return
        if wait:
            concurrent.futures.wait(current_future)
        else:
            current_future.cancel()

    def _cancel_running_task(self, wait=True):
        """
        will abort current task.
        task_executor signal 'finished' will be blocked but callbacks will be executed to ensure a safe processing
        """
        if self.is_available:
            return

        with block_signals(self._task_executor):
            self._task_executor._cancel_running_task()
            # stop and remove the current task from the stack
            self._task_executor.stop(wait=wait)
            # signal that processing is done
            self._process_ended_direct(task_executor=self._task_executor)

    def _cancel_future(self, future) -> bool:
        task_exec_id = future.task_exec_id
        if task_exec_id in self._task_futures.keys():
            self._cancel_pending_task(task_exec_id=task_exec_id)
            return True
        return False

    def _abort_future(self, future) -> bool:
        if future.task_exec_id == self._current_task_future.task_exec_id:
            self._cancel_running_task()
            return True
        return False

    def _cancel_pending_task(self, task_exec_id: TaskExecutionID):
        future = self._task_futures.pop(task_exec_id, None)
        if future in self._task_queue:
            self._task_queue.remove(future)

    def stop(self):
        """
        stop the queue. Wait for the last processing to be finished and reset current_task
        """
        self._task_executor.finished.disconnect(self._process_ended)
        self._task_queue.clear()
        self._task_futures.clear()
        self._current_task_future = None
        self._task_executor.stop(wait=True)
        self._task_executor = None

    @property
    def current_task(self):
        return self._task_executor.current_task


class _ThreadedTaskExecutor(ThreadedTaskExecutor):
    """Processing thread with some information on callbacks to be executed"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__callbacks = tuple()

    def create_task(
        self,
        _callbacks: Iterable = tuple(),
        _log_missing_inputs: bool = False,
        **kwargs,
    ):
        kwargs["log_missing_inputs"] = _log_missing_inputs
        super().create_task(**kwargs)
        self.__callbacks = _callbacks

    @property
    def callbacks(self):
        """Methods to be executed by the thread once the computation is done"""
        return self.__callbacks
