from AnyQt.QtCore import QObject
from AnyQt.QtCore import pyqtSignal as Signal
from ewokscore.progress import BasePercentageProgress


class QProgress(QObject, BasePercentageProgress):
    """Progress associated to a QObject used as an Ewoks task argument
    to report task execution progress."""

    sigProgressChanged = Signal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _update(self):
        self.sigProgressChanged.emit(self._progress)
