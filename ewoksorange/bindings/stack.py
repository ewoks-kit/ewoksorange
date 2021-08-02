from queue import Queue
from AnyQt.QtCore import QObject
from AnyQt.QtCore import pyqtSignal as Signal
from .taskexecutor import _ProcessingThread
from typing import Union
from typing import Iterable


class FIFOTaskStack(QObject, Queue):
    """Processing Queue with a First In, First Out behavior"""

    sigComputationStarted = Signal()
    """Signal emitted when a computation is started"""
    sigComputationEnded = Signal()
    """Signal emitted when a computation is ended"""

    def __init__(self, ewokstaskclass, taskprogress):
        super().__init__()
        self._processingThread = _StackProcessingThread(
            taskprogress=taskprogress, ewokstaskclass=ewokstaskclass
        )
        self._processingThread.finished.connect(self._process_ended)
        self._available = True
        """Simple thread to know if we can do some processing
        and avoid to mix thinks with QSignals and different threads
        """

    @property
    def is_available(self) -> bool:
        return self._available

    def add(self, varinfo=None, inputs=None, callbacks: Union[Iterable, None] = None):
        """Add a task `ewokstaskclass` execution request"""
        super().put((varinfo, inputs, callbacks or tuple()))

        if self.is_available:
            self._process_next()

    def _process_next(self):
        if Queue.empty(self):
            return

        self._available = False
        varinfo, inputs, callbacks = Queue.get(self)
        self._processingThread.init(varinfo=varinfo, inputs=inputs, callbacks=callbacks)
        self.sigComputationStarted.emit()
        self._processingThread.start()

    def _process_ended(self):
        for callback in self.sender().callbacks:
            callback()
        self.sigComputationEnded.emit()
        self._available = True
        if self.is_available:
            self._process_next()

    def stop(self):
        while not self.empty():
            self.get()
        self._processingThread.blockSignals(True)
        self._processingThread.wait()


class _StackProcessingThread(_ProcessingThread):
    """Processing thread with some information on callbacks to be executed"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._callbacks = tuple()

    def init(self, callbacks=None, *args, **kwargs):
        super().init(*args, **kwargs)
        self._callbacks = callbacks or tuple()

    @property
    def callbacks(self):
        """callback to be executed by the thread once the computation is done"""
        return self._callbacks
