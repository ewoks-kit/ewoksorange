"""MyWidget.py: contains GUI specific code"""

from silx.gui import qt


class MyWidget(qt.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setLayout(qt.QFormLayout())

        self._minPercentiles = qt.QSlider(qt.Qt.Orientation.Horizontal)
        self._minPercentiles.setTickPosition(qt.QSlider.TickPosition.TicksBelow)
        self._minPercentiles.setEnabled(False)
        self._minPercentiles.setRange(0, 100)
        self._minPercentiles.setTickInterval(10)
        self.layout().addRow(
            "min percentiles",
            self._minPercentiles,
        )

        # max percentiles
        self._maxPercentiles = qt.QSlider(qt.Qt.Orientation.Horizontal)
        self._maxPercentiles.setTickPosition(qt.QSlider.TickPosition.TicksBelow)
        self._maxPercentiles.setEnabled(False)
        self._maxPercentiles.setRange(0, 100)
        self._maxPercentiles.setTickInterval(10)
        self.layout().addRow(
            "max percentiles",
            self._maxPercentiles,
        )

    def setPercentiles(self, percentiles: tuple):
        self._minPercentiles.setValue(percentiles[0])
        self._maxPercentiles.setValue(percentiles[1])
