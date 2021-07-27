from Orange.widgets.widget import OWWidget
import ewoksorange.tests.listoperations
from Orange.widgets import gui
from Orange.widgets.widget import Input, Output
from AnyQt.QtCore import pyqtSignal as Signal
from AnyQt.QtCore import QThread
import logging
from typing import Iterable

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
        self._processingThread = ProcessingThread()
        self._progress = gui.ProgressBar(self, 100)
        self._processingThread.sigProgress.connect(self._setProgressValue)
        self._processingThread.finished.connect(self._processingFinished)

    @Inputs.list_
    def compute_sum(self, iterable):
        if self._processingThread.isRunning():
            _logger.error("A processing is already on going")
            return
        self._processingThread.init(iterable)
        self._processingThread.start()

    def _setProgressValue(self, value):
        self._progress.widget.progressBarSet(value)

    def _processingFinished(self):
        sum_ = self._processingThread.sum_
        self.Outputs.sum_.send(sum_)


class ProcessingThread(QThread):
    sigProgress = Signal(float)

    def init(self, iterable: Iterable):
        self._iterable = iterable
        self.sum_ = 0

    def run(self):
        self.sum_ = 0
        n_elmt = len(self._iterable)
        for i_elmt, elmt in enumerate(self._iterable):
            self.sum_ += elmt
            if i_elmt % 100:
                # avoid sending one signal per addition
                self.sigProgress.emit((i_elmt / n_elmt) * 100.0)
        self.sigProgress.emit(100.0)
