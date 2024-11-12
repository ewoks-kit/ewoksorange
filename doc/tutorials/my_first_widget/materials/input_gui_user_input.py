from silx.gui import qt
from ewokscore.task import Task
from ewoksorange.bindings.owwidgets import OWEwoksWidgetOneThread
from ewokscore.missing_data import is_missing_data

import numpy


class ClipDataTask(
    Task,
    input_names=["data", "percentiles"],
    output_names=["data"],
):
    """
    Task to rescale 'data' (numpy array) to the given percentiles.
    """

    def run(self):
        data = self.inputs.data
        # compute data min and max
        percentiles = self.inputs.percentiles
        assert (
            isinstance(percentiles, tuple) and len(percentiles) == 2
        ), "incoherent input"
        assert percentiles[0] <= percentiles[1], "incoherent percentiles value"
        print("compute with", percentiles)

        self.outputs.data = numpy.clip(
            data,
            a_min=numpy.percentile(data, percentiles[0]),
            a_max=numpy.percentile(data, percentiles[1]),
        )


class ClipDataOW(
    OWEwoksWidgetOneThread,
    ewokstaskclass=ClipDataTask,
):
    name = "rescale data"
    id = "orange.widgets.my_project.ClipDataTask"
    description = "widget to clip data (numpy array) within a percentile range."
    want_main_area = True
    want_control_area = False

    _ewoks_inputs_to_hide_from_orange = ("percentiles",)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._myWidget = MyWidget(self)
        self.mainArea.layout().addWidget(self._myWidget)

        # set up percentiles
        self._myWidget.setPercentiles((10, 90))

        # connect signal / slot
        self._myWidget._minPercentiles.valueChanged.connect(self._percentileChanged)
        self._myWidget._maxPercentiles.valueChanged.connect(self._percentileChanged)

    def _percentileChanged(self):
        self.set_dynamic_input("percentiles", self._myWidget.getPercentiles())
        self.execute_ewoks_task()


class MyWidget(qt.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setLayout(qt.QFormLayout())

        self._minPercentiles = qt.QSlider(qt.Qt.Orientation.Horizontal)
        self._minPercentiles.setTickPosition(qt.QSlider.TickPosition.TicksBelow)
        self._minPercentiles.setRange(0, 100)
        self._minPercentiles.setTickInterval(10)
        self.layout().addRow(
            "min percentiles",
            self._minPercentiles,
        )

        # max percentiles
        self._maxPercentiles = qt.QSlider(qt.Qt.Orientation.Horizontal)
        self._maxPercentiles.setTickPosition(qt.QSlider.TickPosition.TicksBelow)
        self._maxPercentiles.setRange(0, 100)
        self._maxPercentiles.setTickInterval(10)
        self.layout().addRow(
            "max percentiles",
            self._maxPercentiles,
        )

    def setPercentiles(self, percentiles: tuple):
        self._minPercentiles.setValue(percentiles[0])
        self._maxPercentiles.setValue(percentiles[1])

    def getPercentiles(self) -> tuple:
        return (self._minPercentiles.value(), self._maxPercentiles.value())
