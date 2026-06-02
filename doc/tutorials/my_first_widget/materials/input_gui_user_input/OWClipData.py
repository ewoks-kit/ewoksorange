"""
OWClipData.py: Code for the orange add-on binding.
"""

from ewokstesttuto.gui.MyWidget import MyWidget
from ewokstesttuto.tasks.clipdata import ClipDataTask

from ewoksorange.gui.owwidgets.threaded import OWEwoksWidgetOneThread


class OWClipData(
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
