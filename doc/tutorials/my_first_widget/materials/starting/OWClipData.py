"""
OWClipData.py: Code for the orange add-on binding.
"""

from ewoksorange.gui.owwidgets.threaded import OWEwoksWidgetOneThread
from ewokstesttuto.tasks.clipdata import ClipDataTask


class OWClipData(
    OWEwoksWidgetOneThread,
    ewokstaskclass=ClipDataTask,
):

    name = "rescale data"

    id = "orange.widgets.my_project.ClipDataTask"

    description = "widget to clip data (numpy array) within a percentile range."

    pass
