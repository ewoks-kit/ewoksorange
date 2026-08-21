from ewokscore.task import Task
from ewoksutils.import_utils import qualname

from ...bindings import execute_graph
from ...gui.orange_utils.signals import Input
from ...gui.orange_utils.signals import Output
from ...gui.owwidgets.base import OWWidget
from ...gui.owwidgets.nothread import OWEwoksWidgetNoThread
from ...gui.owwidgets.registration import register_owwidget
from ...gui.workflows.owscheme import ewoks_to_ows


class Mother(int): ...


class SubClass(Mother): ...


class NativeWidget(OWWidget):
    name = "native widget"

    class Inputs:
        data = Input("data", type=Mother)

    class Outputs:
        data = Output("data", type=Mother)

    @Inputs.data
    def data_received(self, data):
        self.Outputs.data.send(data)


class EwoksTask(
    Task,
    input_names=(),
    output_names=("data",),
):
    def run(self):
        self.outputs.data = SubClass(2)


class EwoksOrangeWidget(OWEwoksWidgetNoThread, ewokstaskclass=EwoksTask):
    name = "ewoks widget"


def test_dynamic_link(tmp_path, orange_canvas_handler):
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

    for widget in (NativeWidget, EwoksOrangeWidget):
        register_owwidget(
            widget_class=widget,
            package_name="ewoksorange",
            category_name="test",
            project_name="ewoksorange",
        )

    destination = str(tmp_path / "ewoksgraph.ows")
    ewoks_to_ows(workflow, destination)

    results = execute_graph(
        destination,
        outputs=[{"id": "1"}],
        no_gui=True,
        timeout=10,
        orange_canvas_handler=orange_canvas_handler,
    )
    assert results == {"data": 2}
