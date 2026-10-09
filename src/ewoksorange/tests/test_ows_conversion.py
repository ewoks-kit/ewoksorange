import io
from collections import namedtuple

try:
    from importlib.resources import files as resource_files
except ImportError:
    from importlib_resources import files as resource_files

import pytest
from ewokscore import load_graph
from ewokscore.tests.examples.graphs import get_graph
from ewokscore.tests.examples.graphs import graph_names

from ..gui.workflows import owscheme
from ..gui.workflows.owscheme import _native_widget_project_name
from ..gui.workflows.owscheme import _read_ewoks_graph_attrs
from ..gui.workflows.owscheme import ewoks_to_ows
from ..gui.workflows.owscheme import graph_is_supported
from ..gui.workflows.owscheme import ows_to_ewoks
from ..gui.workflows.owscheme import read_ows

_FakeEntryPoint = namedtuple("_FakeEntryPoint", ["target", "dist"])


def _make_widget_class(module_name, category="Unknown", name="OWFake"):
    widget_class = type(name, (), {"category": category})
    widget_class.__module__ = module_name
    return widget_class


@pytest.fixture
def patch_pkg_meta(monkeypatch):
    """Patch the entry-point lookup used by `_native_widget_project_name`.

    `entry_points` is set up so `get_entry_point_module_name`/`get_distribution_name`
    just return the fake entry point's fields directly, decoupling the test
    from the real importlib.metadata/pkg_resources objects.
    """

    def _patch(entry_points):
        monkeypatch.setattr(
            owscheme.pkg_meta, "entry_points", lambda group: entry_points
        )
        monkeypatch.setattr(
            owscheme.pkg_meta, "get_entry_point_module_name", lambda ep: ep.target
        )
        monkeypatch.setattr(
            owscheme.pkg_meta, "get_distribution_name", lambda dist: dist
        )

    return _patch


def test_native_widget_project_name_exact_module_match(patch_pkg_meta):
    """test '_native_widget_project_name' with a widget module that exactly matches a registered entry point"""
    patch_pkg_meta([_FakeEntryPoint("orangecontrib.ewoksdemo", "ewoksorange")])
    widget_class = _make_widget_class("orangecontrib.ewoksdemo")

    assert _native_widget_project_name(widget_class) == "ewoksorange"


def test_native_widget_project_name_longest_match_wins(patch_pkg_meta):
    """When several registered entry points are prefixes of the widget's module,
    the most specific (longest) one is the actual owning distribution."""
    entry_points = [
        _FakeEntryPoint("orangecontrib.foo", "distro_a"),
        _FakeEntryPoint("orangecontrib.foo.bar", "distro_b"),
    ]
    widget_class = _make_widget_class("orangecontrib.foo.bar.owwidget")

    patch_pkg_meta(entry_points)
    assert _native_widget_project_name(widget_class) == "distro_b"


def test_native_widget_project_name_falls_back_to_dynamic_registration(
    patch_pkg_meta, monkeypatch
):
    """test '_native_widget_project_name'  and dynamic project names"""
    patch_pkg_meta([])
    monkeypatch.setattr(
        owscheme, "get_dynamic_widget_project_name", lambda qualname: "dynamic_distro"
    )
    widget_class = _make_widget_class("some.random.module")

    assert _native_widget_project_name(widget_class) == "dynamic_distro"


def test_ows_to_ewoks_sumtask_tutorial(tmp_path, qtbot):
    """Test conversion of orange worflow files to ewoks and back"""
    from orangecontrib.ewokstest import tutorials

    filename = resource_files(tutorials).joinpath("sumtask_tutorial.ows")
    ewoksgraph = ows_to_ewoks(str(filename))

    destination = str(tmp_path / "ewoksgraph.ows")
    ewoks_to_ows(ewoksgraph, destination, error_on_duplicates=False)
    ewoksgraph2 = ows_to_ewoks(destination)
    assert ewoksgraph == ewoksgraph2


def test_ows_to_ewoks_sumlist_tutorial(tmp_path, qtbot):
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


_GRAPH_WITH_ATTRS = {
    "graph": {
        "id": "graph_with_attrs",
        "label": "Graph with attributes",
        "requirements": ["numpy"],
        "input_schema": {"a": {"type": "integer"}},
    },
    "nodes": [
        {
            "id": "sum",
            "task_type": "class",
            "task_identifier": "ewokscore.tests.examples.tasks.sumtask.SumTask",
            "default_inputs": [{"name": "a", "value": 1}],
        }
    ],
    "links": [],
}

_EXTRA_GRAPH_ATTRS = {
    "requirements": ["numpy"],
    "input_schema": {"a": {"type": "integer"}},
}


def _assert_extra_graph_attrs(graph_attrs: dict):
    for key, value in _EXTRA_GRAPH_ATTRS.items():
        assert graph_attrs.get(key) == value, key


@pytest.mark.parametrize("from_stream", [False, True])
def test_ows_to_ewoks_keeps_graph_attrs(tmp_path, from_stream):
    filename = str(tmp_path / "workflow.ows")
    ewoks_to_ows(_GRAPH_WITH_ATTRS, filename)

    if from_stream:
        with open(filename, "rb") as stream:
            ewoksgraph = ows_to_ewoks(stream)
            assert stream.tell() == 0  # stream position must be preserved
    else:
        ewoksgraph = ows_to_ewoks(filename)

    _assert_extra_graph_attrs(ewoksgraph.graph.graph)


def test_canvas_save_and_export_keep_graph_attrs(orange_canvas_handler, tmp_path):
    orange_canvas_handler.load_graph(_GRAPH_WITH_ATTRS)
    scheme = orange_canvas_handler.scheme

    # "File > Save"
    filename = str(tmp_path / "saved.ows")
    assert orange_canvas_handler.canvas.save_scheme_to(scheme, filename)
    _assert_extra_graph_attrs(_read_ewoks_graph_attrs(filename))
    _assert_extra_graph_attrs(ows_to_ewoks(filename).graph.graph)

    # "File > Export Ewoks workflow..." converts the scheme saved in memory
    buffer = io.BytesIO()
    scheme.save_to(buffer, pretty=True, pickle_fallback=True)
    buffer.seek(0)
    _assert_extra_graph_attrs(ows_to_ewoks(buffer).graph.graph)


def test_read_ows_and_graph_attrs_do_not_consume_stream(tmp_path):
    filename = str(tmp_path / "workflow.ows")
    ewoks_to_ows(_GRAPH_WITH_ATTRS, filename)

    with open(filename, "rb") as stream:
        ows = read_ows(stream)
        assert stream.tell() == 0
        # Call order does not matter: the stream is still fully readable
        _assert_extra_graph_attrs(_read_ewoks_graph_attrs(stream))
        assert stream.tell() == 0
        assert read_ows(stream).title == ows.title
        assert stream.tell() == 0
