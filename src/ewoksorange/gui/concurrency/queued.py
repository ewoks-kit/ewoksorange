from queue import Queue
from typing import Iterable

from AnyQt.QtCore import QObject
from AnyQt.QtCore import pyqtSignal as Signal

from ..qt_utils.signals import block_signals
from .threaded import ThreadedTaskExecutor


class TaskExecutorQueue(QObject, Queue):
    """Processing Queue with a First In, First Out behavior"""

    sigComputationStarted = Signal()
    """Signal emitted when a computation is started"""
    sigComputationEnded = Signal()
    """Signal emitted when a computation is ended"""

    def __init__(self, ewokstaskclass):
        super().__init__()
        self._task_executor = _ThreadedTaskExecutor(ewokstaskclass=ewokstaskclass)
        self._task_executor.finished.connect(self._process_ended)
        self._available = True
        """Simple thread to know if we can do some processing
        and avoid to mix thinks with QSignals and different threads
        """

    @property
    def is_available(self) -> bool:
        return self._available

    def add(self, **kwargs):
        """Add a task `ewokstaskclass` execution request"""
        super().put(kwargs)
        if self.is_available:
            self._process_next()

    def _process_next(self):
        if Queue.empty(self):
            return
        self._available = False
        self._task_executor.create_task(**Queue.get(self))
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
        if self.is_available:
            self._process_next()

    def cancel_running_task(self, wait=True):
        """
        will cancel current task.
        task_executor signal 'finished' will be blocked but callbacks will be executed to ensure a safe processing
        """
        if not self.is_available:
            with block_signals(self._task_executor):
                self._task_executor.cancel_running_task()
                # stop and remove the current task from the stack
                self._task_executor.stop(wait=wait)
                # signal that processing is done
                self._process_ended_direct(task_executor=self._task_executor)

    def stop(self):
        """
        stop the queue. Wait for the last processing to be finished and reset current_task
        """
        self._task_executor.finished.disconnect(self._process_ended)
        while not self.empty():
            self.get()
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
