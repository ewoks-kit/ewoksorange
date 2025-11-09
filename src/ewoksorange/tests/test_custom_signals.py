from ewokscore.tests.examples.tasks.sumtask import SumTask

from ..gui.orange_utils.signals import Input
from ..gui.orange_utils.signals import Output
from ..gui.owwidgets.nothread import OWEwoksWidgetNoThread
from .utils import execute_task


class CustomSignalsWidget(OWEwoksWidgetNoThread, ewokstaskclass=SumTask):
    name = "custom_signals"

    class Inputs:
        c = Input("A", object, ewoksname="a")
        d = Input("B", object, ewoksname="b")

    class Outputs:
        e = Output("A + B", object, ewoksname="result")


def test_execute_custom_signals_widget(qtapp):
    result = execute_task(CustomSignalsWidget, inputs={"a": 5, "b": 6})
    expected = {"result": 11}
    assert result == expected, result
