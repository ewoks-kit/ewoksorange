import json

try:
    from importlib.resources import files as resource_files
except ImportError:
    from importlib_resources import files as resource_files

from orangecanvas.scheme import Scheme
from orangecanvas.scheme import SchemeTextAnnotation

from ..gui.canvas.handler import OrangeCanvasHandler
from ..gui.canvas.mainwindow import EWOKS_FILE_FILTER
from ..gui.workflows.owscheme import node_data_to_properties
from ..gui.workflows.owscheme import read_ows


def _ows_content(filename: str) -> dict:
    scheme = read_ows(filename)
    return {
        "title": scheme.title,
        "description": scheme.description,
        "nodes": [
            (node, node_data_to_properties(node.data))
            for node in (node._replace(data=None) for node in scheme.nodes)
        ],
        "links": scheme.links,
        "annotations": scheme.annotations,
        "session_state": scheme.session_state,
    }


def test_open_dialog_has_ewoks_filter(ewoksorange_qtapp):
    with OrangeCanvasHandler() as handler:
        dialog = handler.canvas._open_workflow_dialog()
        assert EWOKS_FILE_FILTER in dialog.nameFilters()
        dialog.close()


def test_save_and_open_ewoks_workflow(tmp_path, ewoksorange_qtapp):
    """Saving as an Ewoks workflow and opening it again keeps everything"""
    from orangecontrib.ewokstest import tutorials

    ows_filename = str(resource_files(tutorials).joinpath("sumtask_tutorial.ows"))
    initial_filename = str(tmp_path / "initial.ows")
    expected_filename = str(tmp_path / "expected.ows")
    json_filename = str(tmp_path / "workflow.json")
    roundtrip_filename = str(tmp_path / "roundtrip.ows")

    with OrangeCanvasHandler() as handler:
        canvas = handler.canvas
        canvas.load_scheme(ows_filename)

        # Orange information without ewoks equivalent
        scheme = handler.scheme
        scheme.title = ""
        scheme.links[0].set_enabled(False)
        scheme.add_annotation(SchemeTextAnnotation((0.0, 0.0, 100.0, 20.0), "note"))
        scheme.set_window_group_presets(
            [Scheme.WindowGroup("group", True, [(scheme.nodes[0], b"state")])]
        )

        # Reload to have the widget settings in the saved properties
        assert canvas.save_scheme_to(scheme, initial_filename)
        canvas.load_scheme(initial_filename)
        scheme = handler.scheme

        assert canvas.save_scheme_to(scheme, expected_filename)
        assert canvas.save_scheme_to(scheme, json_filename)

        with open(json_filename) as f:
            graph = json.load(f)
        assert [node["label"] for node in graph["nodes"]] == [
            node.title for node in scheme.nodes
        ]

        canvas.load_scheme(json_filename)
        assert canvas.current_document().path() == json_filename
        assert canvas.save_scheme_to(handler.scheme, roundtrip_filename)

        # Saving again gives the same Ewoks workflow
        assert canvas.save_scheme_to(handler.scheme, json_filename)
        with open(json_filename) as f:
            assert json.load(f) == graph

    assert _ows_content(roundtrip_filename) == _ows_content(expected_filename)
