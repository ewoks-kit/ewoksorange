import pytest
from ewokscore import Task

from ..gui.owwidgets.meta import ow_build_opts
from ..gui.owwidgets.nothread import OWEwoksWidgetNoThread


class DummyTask(
    Task,
    input_names=("visible_input", "hidden_input"),
    output_names=("visible_output", "hidden_output"),
):
    def run(self):
        self.outputs.visible_output = self.inputs.visible_input
        self.outputs.hidden_output = self.inputs.hidden_input


class OWDummyWidget(OWEwoksWidgetNoThread, **ow_build_opts, ewokstaskclass=DummyTask):
    name = "test_hidden"
    _ewoks_inputs_to_hide_from_orange = ("hidden_input",)
    _ewoks_outputs_to_hide_from_orange = ("hidden_output",)


@pytest.mark.parametrize(
    "exclude_hidden, expected",
    [
        pytest.param(
            False,
            {"visible_input": "visible", "hidden_input": "hidden"},
            id="include-hidden",
        ),
        pytest.param(True, {"visible_input": "visible"}, id="exclude-hidden"),
    ],
)
def test_hidden_inputs(qtapp, exclude_hidden, expected):
    widget = OWDummyWidget()

    widget.set_default_input("visible_input", "visible_default")
    widget.set_default_input("hidden_input", "hidden_default")

    widget.set_dynamic_input("visible_input", "visible")
    widget.set_dynamic_input("hidden_input", "hidden")

    default_expected = {k: f"{v}_default" for k, v in expected.items()}
    actual = widget.get_default_input_names(exclude_hidden=exclude_hidden)
    assert set(actual) == set(default_expected)
    actual = widget.get_default_input_values(exclude_hidden=exclude_hidden)
    assert actual == default_expected

    actual = widget.get_dynamic_input_names(exclude_hidden=exclude_hidden)
    assert set(actual) == set(expected)
    actual = widget.get_dynamic_input_values(exclude_hidden=exclude_hidden)
    assert actual == expected

    actual = widget.get_input_names(exclude_hidden=exclude_hidden)
    assert set(actual) == set(expected)
    actual = widget.get_task_inputs(exclude_hidden=exclude_hidden)
    assert actual == expected
    actual = widget.get_task_input_values(exclude_hidden=exclude_hidden)
    assert actual == expected


@pytest.mark.parametrize(
    "exclude_hidden, expected",
    [
        pytest.param(
            False,
            {"visible_output": "visible", "hidden_output": "hidden"},
            id="include-hidden",
        ),
        pytest.param(True, {"visible_output": "visible"}, id="exclude-hidden"),
    ],
)
def test_hidden_outputs(qtapp, exclude_hidden, expected):
    widget = OWDummyWidget()

    widget.set_default_input("visible_input", "visible_default")
    widget.set_default_input("hidden_input", "hidden_default")

    widget.set_dynamic_input("visible_input", "visible")
    widget.set_dynamic_input("hidden_input", "hidden")

    widget.handleNewSignals()

    actual = widget.get_output_names(exclude_hidden=exclude_hidden)
    assert set(actual) == set(expected)
    actual = widget.get_task_outputs(exclude_hidden=exclude_hidden)
    assert actual == expected
    actual = widget.get_task_output_values(exclude_hidden=exclude_hidden)
    assert actual == expected
