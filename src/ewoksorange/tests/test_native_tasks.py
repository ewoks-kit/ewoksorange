import pytest

from ..gui.owwidgets.base import OWWidget
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
        from oasys.widgets.tools.ow_python_script import Script

        settings = {
            "auto_execute": True,
            "currentScriptIndex": 0,
            "libraryListSource": [Script("test_script", "out_object = [1, 2, 3]")],
        }
        expected = {"out_object": [1, 2, 3]}
    elif ORANGE_VERSION == ORANGE_VERSION.latest_orange:
        from Orange.widgets.data.owpythonscript import OWPythonScript

        settings = {
            "scriptText": "out_object = [1, 2, 3]",
            "scriptLibrary": [],
            "__version__": 2,
        }
        expected = {
            "data": None,
            "learner": None,
            "classifier": None,
            "object": [1, 2, 3],
        }
    else:
        pytest.skip("Requires the Orange3 or Oasys1 python script widget")

    result = execute_task(OWPythonScript, settings=settings)
    assert result == expected, result
