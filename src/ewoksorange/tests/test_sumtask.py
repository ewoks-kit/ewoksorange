import pytest
from ewokscore.inittask import instantiate_task
from ewokscore.task import TaskInputError
from ewoksutils.import_utils import import_qualname

from ..gui.workflows.task_wrappers import OWWIDGET_TASKS_GENERATOR
from .utils import execute_task

_WIDGETS = [
    "orangecontrib.ewokstest.sumtask.OWSumTaskTest",
]


@pytest.mark.parametrize("widget_qualname", _WIDGETS)
def test_sumtask(widget_qualname, qtapp):
    widget = import_qualname(widget_qualname)
    result = execute_task(widget, inputs={"a": 1, "b": 2})
    assert result == {"result": 3}
    result = execute_task(widget.ewokstaskclass, inputs={"a": 1, "b": 2})
    assert result == {"result": 3}


@pytest.mark.parametrize("widget_qualname", _WIDGETS)
def test_sumtask_task_generator(widget_qualname, qtapp):
    node_attrs = {
        "task_type": "generated",
        "task_identifier": widget_qualname,
        "task_generator": OWWIDGET_TASKS_GENERATOR,
    }
    task = instantiate_task("node_id", node_attrs, inputs={"a": 1, "b": 2})
    task.execute()
    assert task.get_output_values() == {"result": 3}


@pytest.mark.parametrize("widget_qualname", _WIDGETS)
def test_sumtask_missing_inputs(widget_qualname, qtapp):
    node_attrs = {
        "task_type": "generated",
        "task_identifier": widget_qualname,
        "task_generator": OWWIDGET_TASKS_GENERATOR,
    }
    with pytest.raises(TaskInputError):
        instantiate_task("node_id", node_attrs)
