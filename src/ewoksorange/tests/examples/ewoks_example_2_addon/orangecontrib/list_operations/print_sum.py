from ewoksorange.bindings import OWEwoksWidgetNoThread
from ewoksorange.tests.listoperations import PrintSum
from ewoks_example_2_addon.widgets import WidgetMixin


class PrintSumOW(WidgetMixin, OWEwoksWidgetNoThread, ewokstaskclass=PrintSum):
    name = "Print list sum"
    description = "Print received list sum"
    icon = "icons/mywidget.svg"
    want_main_area = True
