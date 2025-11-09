from ewokscore.tests.examples.tasks.sumtask import SumTask

from ewoksorange.gui.orange_utils.signals import Input
from ewoksorange.gui.orange_utils.signals import Output
from ewoksorange.gui.owwidgets.threaded import OWEwoksWidgetOneThread
from ewoksorange.gui.widgets.simple_types_mixin import IntegerAdderMixin

__all__ = ["SumTask"]


class OWSumTask(IntegerAdderMixin, OWEwoksWidgetOneThread, ewokstaskclass=SumTask):
    name = "SumTask"
    description = "Adds two numbers"
    icon = "icons/sum.png"
    want_main_area = True

    class Inputs:
        a = Input("A", object)
        b = Input("B", object)

    class Outputs:
        result = Output("A + B", object)
