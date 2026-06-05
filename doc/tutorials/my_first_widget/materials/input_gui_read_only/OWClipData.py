"""
OWClipData.py: Code for the orange add-on binding.
"""

from ewokscore.missing_data import is_missing_data
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

    def handleNewSignals(self):
        percentiles = self.get_task_input_value("percentiles")
        if not is_missing_data(percentiles):
            self._myWidget.setPercentiles(percentiles)

        return super().handleNewSignals()
