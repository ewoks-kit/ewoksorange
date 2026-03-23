from ewokscore.tests.examples.tasks.sumtask import SumTask

from ..gui.owwidgets.nothread import OWEwoksWidgetNoThread
from .utils import execute_task


class OWSumTask(OWEwoksWidgetNoThread, ewokstaskclass=SumTask):
    pass


def test_widget_without_explicit_name():
    result = execute_task(OWSumTask, inputs={"a": 10, "b": 3})
    assert result == {"result": 13}
