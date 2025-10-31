from ewoksorange.gui.owwidgets.nothread import OWEwoksWidgetNoThread
from ewoksorange.tests.examples.tasks import PrintSum
from ewoksorange.tests.examples.widgets import WidgetMixin


class PrintSumOW(WidgetMixin, OWEwoksWidgetNoThread, ewokstaskclass=PrintSum):
    name = "Print list sum"
    description = "Print received list sum"
    icon = "icons/mywidget.svg"
    want_main_area = True
