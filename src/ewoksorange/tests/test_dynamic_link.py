from ..bindings.owwidgets import OWEwoksWidgetNoThread, OWWidget
from ..bindings.owsignals import Input
from ..orange_version import ORANGE_VERSION

import pytest
import xml.etree.cElementTree as ET

from ewokscore.task import Task
from ewoksutils.import_utils import qualname
from ewoksorange.registration import register_owwidget


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
    root = ET.Element("scheme", version="2.0", title="", description="")
    nodes = ET.SubElement(root, "nodes")
    # ewoks widget
    ET.SubElement(
        nodes,
        "node",
        id="0",
        name="ewoks widget",
        qualified_name=qualname(EwoksOrangeWidget),
        project_name="ewoksorange",
        position="(100.0, 156.0)",
    )
    # native widget
    ET.SubElement(
        nodes,
        "node",
        id="1",
        name="native widget",
        qualified_name=qualname(NativeWidget),
        project_name="ewoksorange",
        position="(200.0, 156.0)",
    )

    links = ET.SubElement(root, "links")
    # link
    ET.SubElement(
        links,
        "link",
        id="0",
        source_node_id="0",
        sink_node_id="1",
        source_channel="data",
        sink_channel="data",
        enabled="true",
        source_channel_id="data",
        sink_channel_id="data",
    )

    destination = str(tmpdir / "ewoksgraph.ows")
    tree = ET.ElementTree(root)
    tree.write(destination, encoding="utf-8", xml_declaration=True)

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
    native_widget = next(ewoks_orange_canvas.widgets_from_name("native widget"))
    assert native_widget._data == 2
