from Orange.widgets.widget import OWWidget
import ewoksorange.tests.listoperations
from Orange.widgets import gui
from Orange.widgets.widget import Input, Output
from AnyQt.QtCore import pyqtSignal as Signal
from AnyQt.QtCore import QThread
import logging

_logger = logging.getLogger(__name__)


class SumList(OWWidget):
    name = "SumList"

    description = "Sum all elements of a list"

    id = "orangecontrib.list_operations.sumlist.SumList"

    category = "esrfWidgets"

    ewokstaskclass = ewoksorange.tests.listoperations.SumList

    want_main_area = False

    class Inputs:
        list_ = Input("list", list)

    class Outputs:
        sum_ = Output("sum", float)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._progress = gui.ProgressBar(self, 100)
        self._processingThread = None

    @Inputs.list_
    def compute_sum(self, iterable):
        if self._processingThread is not None and self._processingThread.isRunning():
            _logger.error("A processing is already on going")
            return

        self._processingThread = ProcessingThread(inputs={"iterable": iterable})
        self._processingThread.sigProgress.connect(self._setProgressValue)
        self._processingThread.finished.connect(self._processingFinished)
        self._processingThread.start()

    def _setProgressValue(self, value):
        self._progress.widget.progressBarSet(value)

    def _processingFinished(self):
        sum_ = self._processingThread.outputs.sum
        self._processingThread.finished.disconnect(self._processingFinished)
        self.Outputs.sum_.send(sum_)


class ProcessingThread(QThread, ewoksorange.tests.listoperations.SumList):
    sigProgress = Signal(float)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lastProgress = None

    def update_progress(self, progress: float):
        if self._lastProgress != int(progress):
            self._lastProgress = int(progress)
            self.sigProgress.emit(progress)
