from __future__ import annotations

import uuid
from collections import deque
from typing import Any
from typing import Deque
from typing import Dict
from typing import Iterable

from AnyQt.QtCore import QObject
from AnyQt.QtCore import pyqtSignal as Signal

from ..qt_utils.signals import block_signals
from .base import TaskExecutionID
from .threaded import ThreadedTaskExecutor


class TaskExecutorQueue(QObject):
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
        self._task_queue: Deque[TaskExecutionID] = deque()
        """Queue storing task IDs in FIFO order"""
        self._task_exec_ids: Dict[TaskExecutionID, Dict[str, Any]] = {}
        """Dictionary mapping task IDs to their keyword arguments"""
        self._current_task_exec_id: TaskExecutionID | None = None
        self._task_executor: ThreadedTaskExecutor = _ThreadedTaskExecutor(
            ewokstaskclass=ewokstaskclass
        )
        self._task_executor.finished.connect(self._process_ended)
        self._available: bool = True

    @property
    def is_available(self) -> bool:
        return self._available

    def add(self, **kwargs) -> TaskExecutionID:
        """Add a task `ewokstaskclass` execution request

        :return: Task identifier (UUID) that can be used to cancel the task
        """
        task_exec_id = str(uuid.uuid4())
        self._task_exec_ids[task_exec_id] = kwargs
        self._task_queue.append(task_exec_id)

        if self.is_available:
            self._process_next()

        return task_exec_id

    def _process_next(self):
        if not self._task_queue:
            return

        self._available = False
        self._current_task_exec_id = self._task_queue.popleft()
        task_kwargs = self._task_exec_ids.pop(self._current_task_exec_id)

        self._task_executor.create_task(**task_kwargs)
        if self._task_executor.has_task:
            self.sigComputationStarted.emit()
            self._task_executor.start()
        else:
            self._task_executor.finished.emit()

    def _process_ended(self):
        self._process_ended_direct(self.sender())

    def _process_ended_direct(self, task_executor: "_ThreadedTaskExecutor"):
        for callback in task_executor.callbacks:
            callback()
        self.sigComputationEnded.emit()
        self._available = True
        self._current_task_exec_id = None
        if self.is_available:
            self._process_next()

    def cancel_running_task(self, wait=True):
        """
        will abort current task.
        task_executor signal 'finished' will be blocked but callbacks will be executed to ensure a safe processing
        """
        if self.is_available:
            return

        with block_signals(self._task_executor):
            self._task_executor.cancel_running_task()
            # stop and remove the current task from the stack
            self._task_executor.stop(wait=wait)
            # signal that processing is done
            self._process_ended_direct(task_executor=self._task_executor)

    def cancel_task(self, task_exec_id: TaskExecutionID):
        """Cancel a task by its identifier

        :param task_exec_id: The identifier returned by add()
        :return: True if the task was successfully cancelled, False otherwise
        """
        # If task is currently running, use existing cancel method
        if self._current_task_exec_id == task_exec_id:
            self.cancel_running_task()
        else:
            self._cancel_pending_task(task_exec_id)

    def _cancel_pending_task(self, task_exec_id: TaskExecutionID):
        # If task is not currently running, remove from queue
        if task_exec_id in self._task_exec_ids:
            # Remove from queue
            if task_exec_id in self._task_queue:
                self._task_queue.remove(task_exec_id)
                del self._task_exec_ids[task_exec_id]

    def cancel_all_tasks(self, wait=True):
        """Cancel all pending and running tasks in the queue."""
        # first clear the queue of pending tasks
        self._task_queue.clear()
        self._task_exec_ids.clear()
        # then cancel the currently running task, if any
        self.cancel_running_task(wait=wait)

    def stop(self):
        """
        stop the queue. Wait for the last processing to be finished and reset current_task
        """
        self._task_executor.finished.disconnect(self._process_ended)
        self._task_queue.clear()
        self._task_exec_ids.clear()
        self._current_task_exec_id = None
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
