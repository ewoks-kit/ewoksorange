from typing import Optional

from ewokscore.tests.test_workflow_events import fetch_events
from ewokscore.tests.test_workflow_events import run_failed_workfow
from ewokscore.tests.test_workflow_events import run_succesfull_workfow
from ewokscore.tests.test_workflow_events import sqlite_path  # noqa F401

from ..gui.workflows.owscheme import ewoks_to_ows


def test_succesfull_workfow(sqlite_path, ewoks_orange_canvas):  # noqa 811
    database = sqlite_path / "ewoks_events.db"
    run_succesfull_workfow(
        database,
        _execute_graph,
        tempdir=sqlite_path,
        canvas_handler=ewoks_orange_canvas,
    )
    events = fetch_events(database, 14)
    _assert_succesfull_workfow_events(events)


def test_failed_workfow(sqlite_path, ewoks_orange_canvas):  # noqa 811
    database = sqlite_path / "ewoks_events.db"
    run_failed_workfow(
        database,
        _execute_graph,
        tempdir=sqlite_path,
        canvas_handler=ewoks_orange_canvas,
    )
    events = fetch_events(database, 8)
    _assert_failed_workfow_events(events)


def _execute_graph(
    graph, tempdir=None, canvas_handler=None, execinfo: Optional[dict] = None
):
    try:
        filename = str(tempdir / "test_graph.ows")
        ewoks_to_ows(graph, filename, execinfo=execinfo, error_on_duplicates=False)
        canvas_handler.load_ows(filename)
        canvas_handler.start_workflow()
        canvas_handler.wait_widgets(timeout=10, raise_error=False)
    finally:
        # Manually emit the end workflow and job event
        canvas_handler.scheme.ewoks_finalize()


def _assert_succesfull_workfow_events(events):
    # TODO: double event are caused by a handleNewSignals call in the widget constructor
    expected = [
        {"context": "job", "node_id": None, "type": "start"},
        {"context": "workflow", "node_id": None, "type": "start"},
        {"context": "node", "node_id": "node1", "type": "start"},
        {"context": "node", "node_id": "node1", "type": "end"},
        {"context": "node", "node_id": "node2", "type": "start"},
        {"context": "node", "node_id": "node2", "type": "end"},
        {"context": "node", "node_id": "node3", "type": "start"},
        {"context": "node", "node_id": "node3", "type": "end"},
        {"context": "workflow", "node_id": None, "type": "end"},
        {"context": "job", "node_id": None, "type": "end"},
    ]
    captured = [
        {k: event[k] for k in ("context", "node_id", "type")} for event in events
    ]
    assert expected == captured


def _assert_failed_workfow_events(events):
    expected = [
        {"context": "job", "node_id": None, "type": "start", "error_message": None},
        {
            "context": "workflow",
            "node_id": None,
            "type": "start",
            "error_message": None,
        },
        {"context": "node", "node_id": "node1", "type": "start", "error_message": None},
        {"context": "node", "node_id": "node1", "type": "end", "error_message": None},
        {"context": "node", "node_id": "node2", "type": "start", "error_message": None},
        {"context": "node", "node_id": "node2", "type": "end", "error_message": "abc"},
        {
            "context": "node",
            "node_id": "node3",
            "type": "start",
            "error_message": None,
        },  # TODO: caused by clear_downstream
        {
            "context": "node",
            "node_id": "node3",
            "type": "end",
            "error_message": None,
        },  # TODO: caused by clear_downstream
        {
            "context": "workflow",
            "node_id": None,
            "type": "end",
            "error_message": None,  # TODO: should be "Task 'node2' failed"
        },
        {
            "context": "job",
            "node_id": None,
            "type": "end",
            "error_message": None,  # TODO: should be "Task 'node2' failed"
        },
    ]
    captured = [
        {k: event[k] for k in ("context", "node_id", "type", "error_message")}
        for event in events
    ]
    assert expected == captured
