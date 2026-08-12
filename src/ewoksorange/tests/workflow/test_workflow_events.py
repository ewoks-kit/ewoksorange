from typing import Optional

from ewokscore.tests.test_workflow_events import fetch_events
from ewokscore.tests.test_workflow_events import run_failed_workfow
from ewokscore.tests.test_workflow_events import run_succesfull_workfow
from ewokscore.tests.test_workflow_events import sqlite_path  # noqa F401

from ...bindings import execute_graph


def test_succesfull_workfow(sqlite_path):  # noqa 811
    database = sqlite_path / "ewoks_events.db"
    run_succesfull_workfow(database, _execute_graph, tempdir=sqlite_path)
    events = fetch_events(database, 14)
    _assert_succesfull_workfow_events(events)


def test_failed_workfow(sqlite_path):  # noqa 811
    database = sqlite_path / "ewoks_events.db"
    run_failed_workfow(database, _execute_graph, tempdir=sqlite_path)
    events = fetch_events(database, 10)
    _assert_failed_workfow_events(events)


def _execute_graph(graph, tempdir=None, execinfo: Optional[dict] = None):
    try:
        execute_graph(
            graph,
            execinfo=execinfo,
            error_on_duplicates=False,
            tmpdir=str(tempdir),
            no_gui=True,
            timeout=10,
        )
    except Exception:  # noqa: S110
        # A failed task is expected to propagate its raw exception (unlike the
        # sequential engine's wrapped RuntimeError); swallow it here so the
        # workflow/job end events (already flushed by `execute_graph` itself)
        # can be inspected regardless of success or failure.
        pass


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
            "error_message": "abc",
        },
        {
            "context": "job",
            "node_id": None,
            "type": "end",
            "error_message": "abc",
        },
    ]
    captured = [
        {k: event[k] for k in ("context", "node_id", "type", "error_message")}
        for event in events
    ]
    assert expected == captured
