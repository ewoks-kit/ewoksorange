from ewokscore.tests.examples.tasks.sumtask import SumTask

from ewoksorange.gui.orange_imports import Input, Output
from ewoksorange.bindings import OWEwoksWidgetOneThread
from ewoksorange.gui.simpletypesmixin import IntegerAdderMixin


__all__ = ["SumTask"]


class OWSumTask(IntegerAdderMixin, OWEwoksWidgetOneThread, ewokstaskclass=SumTask):
    name = "SumTask"
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
