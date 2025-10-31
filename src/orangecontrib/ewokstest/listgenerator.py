from ewoksorange.gui.owwidgets.nothread import OWEwoksWidgetNoThread
from ewoksorange.tests.examples.tasks import GenerateList
from ewoksorange.tests.examples.widgets import WidgetMixin


class ListGenerator(WidgetMixin, OWEwoksWidgetNoThread, ewokstaskclass=GenerateList):
    name = "List generator"
    description = "Generate a random list with X elements"
    icon = "icons/mywidget.svg"
    want_main_area = True
