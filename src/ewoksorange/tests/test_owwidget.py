from ewokscore import Task

from ewoksorange.bindings import owwidgets
from ewoksorange.bindings import ow_build_opts


def test_set_inputs(qtapp):
    widget = DummyWidget()

    assert_inputs(widget, default={}, dynamic={}, inputs={})

    widget.update_default_inputs(value=99)

    assert_inputs(widget, default={"value": 99}, dynamic={}, inputs={"value": 99})

    widget.update_dynamic_inputs(value=66)

    assert_inputs(
        widget, default={"value": 99}, dynamic={"value": 66}, inputs={"value": 66}
    )


def assert_inputs(widget, default, dynamic, inputs):
    values = widget.get_default_input_values()
    assert values == default

    values = widget.get_dynamic_input_values()
    assert values == dynamic

    values = widget.get_task_input_values()
    assert values == inputs


class DummyTask(
    Task,
    input_names=("value",),
    output_names=("value",),
):
    def run(self):
        self.outputs.value = self.inputs.value


class DummyWidget(
    owwidgets.OWEwoksWidgetOneThreadPerRun,
    **ow_build_opts,
    ewokstaskclass=DummyTask,
):
    pass
