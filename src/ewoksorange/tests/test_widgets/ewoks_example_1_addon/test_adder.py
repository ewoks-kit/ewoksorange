import pytest
from ewoksorange.bindings import OWWIDGET_TASKS_GENERATOR
from ewoksutils.import_utils import import_qualname
from ewokscore.task import TaskInputError
from ewokscore.inittask import instantiate_task
from ewoksorange.tests.utils import execute_task

_WIDGETS = [
    "orangecontrib.ewoks_example_supercategory.ewoks_example_subcategory.adder1.Adder1",
    "orangecontrib.ewoks_example_supercategory.ewoks_example_subcategory.adder2.Adder2",
    "orangecontrib.evaluate.ewoks_example_submodule.adder1.Adder1",
    "orangecontrib.evaluate.ewoks_example_submodule.adder2.Adder2",
    "orangecontrib.ewoks_example_category.adder1.Adder1",
    "orangecontrib.ewoks_example_category.adder2.Adder2",
]


@pytest.mark.parametrize("widget_qualname", _WIDGETS)
def test_adder(register_ewoks_example_1_addon, widget_qualname):
    widget = import_qualname(widget_qualname)
    result = execute_task(widget, inputs={"a": 1, "b": 2})
    assert result == {"result": 3}
    result = execute_task(widget.ewokstaskclass, inputs={"a": 1, "b": 2})
    assert result == {"result": 3}


@pytest.mark.parametrize("widget_qualname", _WIDGETS)
def test_adder_task_generator(widget_qualname, register_ewoks_example_1_addon):
    node_attrs = {
        "task_type": "generated",
        "task_identifier": widget_qualname,
        "task_generator": OWWIDGET_TASKS_GENERATOR,
    }
    task = instantiate_task("node_id", node_attrs, inputs={"a": 1, "b": 2})
    task.execute()
    assert task.get_output_values() == {"result": 3}


@pytest.mark.parametrize("widget_qualname", _WIDGETS)
def test_adder_missing_inputs(widget_qualname, register_ewoks_example_1_addon):
    node_attrs = {
        "task_type": "generated",
        "task_identifier": widget_qualname,
        "task_generator": OWWIDGET_TASKS_GENERATOR,
    }
    with pytest.raises(TaskInputError):
        instantiate_task("node_id", node_attrs)
