from ewoksorange.bindings import OWEwoksWidgetNoThread
from ewoksorange.gui.orange_imports import Input, Output
from ewoksorange.gui.simpletypesmixin import IntegerAdderMixin
from ewoks_example_1_addon.tasks import SumTaskCategory2


__all__ = ["Adder2"]


class Adder2(IntegerAdderMixin, OWEwoksWidgetNoThread, ewokstaskclass=SumTaskCategory2):
    name = "Adder2"
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
