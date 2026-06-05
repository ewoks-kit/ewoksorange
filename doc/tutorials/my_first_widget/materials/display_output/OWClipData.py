"""
OWClipData.py: Code for the orange add-on binding.
"""

import numpy
from ewokscore.missing_data import is_missing_data
from ewokstesttuto.gui.MyWidget import MyWidget
from ewokstesttuto.tasks.clipdata import ClipDataTask
from silx.gui.plot import Plot1D

from ewoksorange.gui.owwidgets.threaded import OWEwoksWidgetOneThread


class OWClipData(
    OWEwoksWidgetOneThread,
    ewokstaskclass=ClipDataTask,
):
    name = "rescale data"
    id = "orange.widgets.my_project.ClipDataTask"
    description = "widget to clip data (numpy array) within a percentile range."
    want_main_area = True
    want_control_area = True

    _ewoks_inputs_to_hide_from_orange = ("percentiles",)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._plot = Plot1D(self)
        self.mainArea.layout().addWidget(self._plot)
        self._myWidget = MyWidget(self)
        self.controlArea.layout().addWidget(self._myWidget)

        # set up percentiles
        self._myWidget.setPercentiles((10, 90))
        self._percentileChanged()

        # connect signal / slot
        self._myWidget._minPercentiles.valueChanged.connect(self._percentileChanged)
        self._myWidget._maxPercentiles.valueChanged.connect(self._percentileChanged)

    def _percentileChanged(self):
        self.set_dynamic_input("percentiles", self._myWidget.getPercentiles())
        data = self.get_task_output_value("data")
        if not is_missing_data(data):
            self.execute_ewoks_task()

    def task_output_changed(self):
        data = self.get_task_output_value("data")
        if is_missing_data(data):
            self._plot.clear()
        else:
            # compute histogram
            histogram, _ = numpy.histogram(data, bins=100, range=(0.0, 1.0))
            self._plot.addCurve(
                x=numpy.linspace(0.0, 1.0, num=100), y=histogram, legend="histogram"
            )
        return super().task_output_changed()
