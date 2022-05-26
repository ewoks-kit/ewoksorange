from ewoksorange.orange_version import ORANGE_VERSION

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    pass
elif ORANGE_VERSION == ORANGE_VERSION.latest_orange:
    from Orange.widgets.widget import Input, Output
else:
    from orangewidget.widget import Input, Output

from ewoksorange.bindings import OWEwoksWidgetNoThread
from ewoks_example_1_addon.tasks import SumTaskSubCategory1
from ewoks_example_1_addon.widgets import IntegerAdderMixin


__all__ = ["Adder1"]


class Adder1(
    IntegerAdderMixin, OWEwoksWidgetNoThread, ewokstaskclass=SumTaskSubCategory1
):
    name = "Adder1"
    description = "Adds two numbers"
    icon = "icons/mywidget.svg"
    want_main_area = True

    if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
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
