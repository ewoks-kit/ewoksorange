from typing import Iterable
from queue import Queue

from AnyQt.QtCore import QObject
from AnyQt.QtCore import pyqtSignal as Signal

from .taskexecutor import ThreadedTaskExecutor


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
        if self._task_executor.is_ready_to_execute:
            self.sigComputationStarted.emit()
            self._task_executor.start()

    def _process_ended(self):
        task_executor = self.sender()
        for callback in task_executor.callbacks:
            callback()
        self.sigComputationEnded.emit()
        self._available = True
        if self.is_available:
            self._process_next()

    def stop(self):
        self._task_executor.finished.disconnect(self._process_ended)
        while not self.empty():
            self.get()
        self._task_executor.stop(wait=True)
        self._task_executor = None


class _ThreadedTaskExecutor(ThreadedTaskExecutor):
    """Processing thread with some information on callbacks to be executed"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__callbacks = tuple()

    def create_task(self, _callbacks: Iterable = tuple(), **kwargs):
        super().create_task(**kwargs)
        self.__callbacks = _callbacks

    @property
    def callbacks(self):
        """Methods to be executed by the thread once the computation is done"""
        return self.__callbacks
