from ewoksorange.bindings import OWEwoksWidgetNoThread
from ewoksorange.tests.listoperations import GenerateList
from ewoks_example_2_addon.widgets import WidgetMixin


class ListGenerator(WidgetMixin, OWEwoksWidgetNoThread, ewokstaskclass=GenerateList):
    name = "List generator"
    description = "Generate a random list with X elements"
    icon = "icons/mywidget.svg"
    want_main_area = True
