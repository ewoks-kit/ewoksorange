try:
    from importlib.resources import files as resource_files
except ImportError:
    from importlib_resources import files as resource_files

import pytest
from ewokscore import load_graph
from ewokscore.tests.examples.graphs import get_graph
from ewokscore.tests.examples.graphs import graph_names

from ..gui.workflows.owscheme import _read_ewoks_graph_attrs
from ..gui.workflows.owscheme import ewoks_to_ows
from ..gui.workflows.owscheme import graph_is_supported
from ..gui.workflows.owscheme import ows_to_ewoks


def test_ows_to_ewoks_sumtask_tutorial(tmp_path, qtapp):
    """Test conversion of orange worflow files to ewoks and back"""
    from orangecontrib.ewokstest import tutorials

    filename = resource_files(tutorials).joinpath("sumtask_tutorial.ows")
    ewoksgraph = ows_to_ewoks(str(filename))

    destination = str(tmp_path / "ewoksgraph.ows")
    ewoks_to_ows(ewoksgraph, destination, error_on_duplicates=False)
    ewoksgraph2 = ows_to_ewoks(destination)
    assert ewoksgraph == ewoksgraph2


def test_ows_to_ewoks_sumlist_tutorial(tmp_path, qtapp):
    """Test conversion of orange worflow files to ewoks and back"""
    from orangecontrib.ewokstest import tutorials

    filename = resource_files(tutorials).joinpath("sumlist_tutorial.ows")
    ewoksgraph = ows_to_ewoks(str(filename))

    destination = str(tmp_path / "ewoksgraph.ows")
    ewoks_to_ows(ewoksgraph, destination)
    ewoksgraph2 = ows_to_ewoks(destination)
    assert ewoksgraph == ewoksgraph2


@pytest.mark.parametrize("graph_name", graph_names())
def test_ewoks_to_ows(graph_name, tmp_path):
    """Test conversion of ewoks to orange worflow files and back"""
    graph, _ = get_graph(graph_name)
    ewoksgraph = load_graph(graph)
    ewoksgraph.graph.graph.pop("ows", None)
    for node_id, node_attrs in ewoksgraph.graph.nodes.items():
        node_attrs["label"] = node_id
        node_attrs.pop("ows", None)
        node_attrs.pop("uiProps", None)

    destination = str(tmp_path / "ewoksgraph2.ows")
    if not graph_is_supported(ewoksgraph):
        with pytest.raises(RuntimeError):
            ewoks_to_ows(ewoksgraph, destination)
        return

    ewoks_to_ows(ewoksgraph, destination, error_on_duplicates=False)
    ewoksgraph2 = ows_to_ewoks(
        destination, title_as_node_id=True, preserve_ows_info=False
    )
    assert ewoksgraph == ewoksgraph2


def test_read_ewoks_graph_attrs_from_path_and_stream(tmp_path):
    content = (
        b'<?xml version="1.0" ?>'
        b"<scheme>"
        b'<ewoks_graph_attrs>{"foo": "bar"}</ewoks_graph_attrs>'
        b"</scheme>"
    )
    filename = tmp_path / "test.ows"
    filename.write_bytes(content)

    assert _read_ewoks_graph_attrs(str(filename)) == {"foo": "bar"}

    with open(filename, "rb") as stream:
        assert _read_ewoks_graph_attrs(stream) == {"foo": "bar"}
        assert stream.tell() == 0  # stream position must be preserved


def test_read_ewoks_graph_attrs_restores_stream_position_on_failure(tmp_path):
    filename = tmp_path / "invalid.ows"
    filename.write_bytes(b"not xml")

    assert _read_ewoks_graph_attrs(str(filename)) is None

    with open(filename, "rb") as stream:
        assert _read_ewoks_graph_attrs(stream) is None
        assert stream.tell() == 0
