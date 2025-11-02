import pytest
from ewokscore.task import Task
from ewoksutils.import_utils import qualname

from ..gui.orange_utils.signals import Input
from ..gui.owwidgets.base import OWWidget
from ..gui.owwidgets.nothread import OWEwoksWidgetNoThread
from ..gui.owwidgets.registration import register_owwidget
from ..gui.workflows.owscheme import ewoks_to_ows
from ..orange_version import ORANGE_VERSION


class Mother(int): ...


class SubClass(Mother): ...


if ORANGE_VERSION != ORANGE_VERSION.oasys_fork:
    # else with oasys we need to provide the 'handler' mechanism
    class NativeWidget(OWWidget):
        name = "native widget"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._data = None

        class Inputs:
            data = Input("data", type=Mother)

        @Inputs.data
        def data_received(self, data):
            self._data = data


class EwoksTask(
    Task,
    input_names=(),
    output_names=("data",),
):
    def run(self):
        self.outputs.data = SubClass(2)


class EwoksOrangeWidget(OWEwoksWidgetNoThread, ewokstaskclass=EwoksTask):
    name = "ewoks widget"


@pytest.mark.skipif(
    ORANGE_VERSION == ORANGE_VERSION.oasys_fork, reason="hanging with oasys binding."
)
def test_dynamic_link(tmpdir, ewoks_orange_canvas):
    """Test that a dynamic link in orange will be processed as expected."""
    # Create an Orange workflows
    workflow = {
        "graph": {
            "id": "ewoksgraph",
            "label": "Ewoks workflow 'ewoksgraph'",
            "schema_version": "1.1",
        },
        "links": [
            {
                "data_mapping": [{"source_output": "data", "target_input": "data"}],
                "source": "0",
                "target": "1",
            }
        ],
        "nodes": [
            {
                "id": "0",
                "task_identifier": qualname(EwoksTask),
                "task_type": "class",
            },
            {
                "id": "1",
                "task_generator": "ewoksorange.bindings.taskwrapper.owwidget_task_wrapper",
                "task_identifier": qualname(NativeWidget),
                "task_type": "generated",
            },
        ],
    }
    destination = str(tmpdir / "ewoksgraph.ows")
    ewoks_to_ows(workflow, destination)

    for widget in (NativeWidget, EwoksOrangeWidget):
        register_owwidget(
            widget_class=widget,
            package_name="ewoksorange",
            category_name="test",
            project_name="ewoksorange",
        )

    # Load and execute the orange workflow
    ewoks_orange_canvas.load_ows(destination)
    ewoks_orange_canvas.start_workflow()

    ewoks_orange_canvas.wait_widgets(timeout=10)
    native_widget = next(ewoks_orange_canvas.widgets_from_name("1"))
    assert native_widget._data == 2
