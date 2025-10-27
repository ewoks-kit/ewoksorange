from ewoksorange.gui.owwidgets.threaded import OWEwoksWidgetWithTaskStack
from ewoksorange.tests.examples.tasks import SumList3
from ewoksorange.tests.examples.widgets import WidgetMixin


class SumListWithTaskStack(
    WidgetMixin, OWEwoksWidgetWithTaskStack, ewokstaskclass=SumList3
):
    """
    Simple demo class that will process task with a FIFO stack and one thread
    connected with the stack
    """

    name = "SumList with one thread and a stack"
    description = "Sum all elements of a list using a thread and a stack"
    icon = "icons/mywidget.svg"
    want_main_area = True
