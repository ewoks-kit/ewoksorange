import sys

import pytest

from ..gui.owwidgets.base import OWWidget
from ..gui.utils.invalid_data import is_invalid_data
from ..orange_version import ORANGE_VERSION
from .utils import execute_task

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:

    class NativeWidget(OWWidget):
        name = "native"
        inputs = [("A", object, "set_a"), ("B", object, "set_b")]
        outputs = [{"name": "A + B", "id": "A + B", "type": object}]

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._a = 0
            self._b = 0

        def set_a(self, value):
            self._a = value
            self.send("A + B", self._a + self._b)

        def set_b(self, value):
            self._b = value
            self.send("A + B", self._a + self._b)

else:
    from orangewidget.widget import Input
    from orangewidget.widget import Output

    class NativeWidget(OWWidget):
        name = "native"

        class Inputs:
            a = Input("A", object)
            b = Input("B", object)

        class Outputs:
            result = Output("A + B", object)

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._a = 0
            self._b = 0

        @Inputs.a
        def set_a(self, value):
            self._a = value
            self.Outputs.result.send(self._a + self._b)

        @Inputs.b
        def set_b(self, value):
            self._b = value
            self.Outputs.result.send(self._a + self._b)


def test_execute_native_widget(qtapp):
    if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
        result = execute_task(NativeWidget, inputs={"A": 5, "B": 6})
        expected = {"A + B": 11}
    else:
        result = execute_task(NativeWidget, inputs={"a": 5, "b": 6})
        expected = {"result": 11}
    assert result == expected, result


def test_execute_python_script(qtapp):
    if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
        from oasys.widgets.tools.ow_python_script import OWPythonScript

        all_outputs = {"out_object"}
        outputs_with_values = all_outputs
    elif ORANGE_VERSION == ORANGE_VERSION.latest_orange:
        from Orange.widgets.data.owpythonscript import OWPythonScript

        all_outputs = {"data", "learner", "classifier", "object"}
        if sys.platform == "win32":
            # TODO: not sure whether it is a bug in orange or in ewoksorange
            outputs_with_values = {}
        else:
            outputs_with_values = {"data"}
    else:
        pytest.skip("Requires the Orange3 or Oasys1 python script widget")

    result = execute_task(OWPythonScript)
    assert set(result) == all_outputs, result
    for name in outputs_with_values:
        assert not is_invalid_data(result[name]), f"Value of {name!r} not set"
