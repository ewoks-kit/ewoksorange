from ewoksorange.gui.orange_utils.orange_imports import Input
from ewoksorange.gui.orange_utils.orange_imports import Output
from ewoksorange.gui.owwidgets.nothread import OWEwoksWidgetNoThread
from ewoksorange.gui.widgets.simple_types_mixin import IntegerAdderMixin
from ewoksorange.tests.examples.tasks import SumTaskTest

__all__ = ["OWSumTaskTest"]


class OWSumTaskTest(
    IntegerAdderMixin, OWEwoksWidgetNoThread, ewokstaskclass=SumTaskTest
):
    name = "SumTaskTest"
    description = "Adds two numbers"
    icon = "icons/sum.png"
    want_main_area = True

    if Input is None:
        inputs = [("A", object, ""), ("B", object, "")]
        outputs = [{"name": "A + B", "id": "A + B", "type": object}]
        inputs_orange_to_ewoks = {"A": "a", "B": "b"}
        outputs_orange_to_ewoks = {"A + B": "result"}
    else:

        class Inputs:
            a = Input("A", object)
            b = Input("B", object)

        class Outputs:
            result = Output("A + B", object)
