from ..bindings.owwidgets import OWEwoksWidgetNoThread, OWWidget
from ..bindings.owsignals import Input, Output
from ewokscore.task import Task
from ewoksutils.import_utils import qualname
from ewoksorange.bindings import ewoks_to_ows


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
        self.Outputs.data.send(data + 1)


class EwoksTask(
    Task,
    input_names=(),
    output_names=("data",),
):
    def run(self):
        self.outputs.data = SubClass(2)


class EwoksOrangeWidget(OWEwoksWidgetNoThread):
    name = "ewoks widget"


def test_dynamic_link(tmpdir, ewoks_orange_canvas):
    """Test that a dynamic link in orange will be processed as expected."""
    # Create an Orange workflows
    import xml.etree.cElementTree as ET

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
    print("destination is", destination)

    # Load and execute the orange workflow
    ewoks_orange_canvas.load_ows(destination)
    ewoks_orange_canvas.start_workflow()
    # from silx.gui import qt

    # qt.QApplication.instance().exec_()
    ewoks_orange_canvas.wait_widgets(timeout=10)
    results = dict(ewoks_orange_canvas.iter_output_values())

    assert results == {"task1": {"data": SubClass(2)}, "task2": {"b": 3}}
