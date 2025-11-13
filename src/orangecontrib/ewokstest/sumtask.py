from ewoksorange.gui.orange_utils.signals import Input
from ewoksorange.gui.orange_utils.signals import Output
from ewoksorange.gui.owwidgets.nothread import OWEwoksWidgetNoThread
from ewoksorange.gui.widgets.simple_types_mixin import IntegerAdderMixin
from ewoksorange.tests.examples.tasks import SumTaskTest


class OWSumTaskTest(
    IntegerAdderMixin, OWEwoksWidgetNoThread, ewokstaskclass=SumTaskTest
):
    name = "SumTaskTest"
    description = "Adds two numbers"
    icon = "icons/sum.png"
    want_main_area = True

    class Inputs:
        a = Input("A", object)
        b = Input("B", object)

    class Outputs:
        result = Output("A + B", object)
