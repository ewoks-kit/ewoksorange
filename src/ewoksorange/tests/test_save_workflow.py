import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from ewokscore import execute_graph
from ewoksutils.import_utils import qualname

from orangecontrib.ewokstools.save_workflow import OWSaveWorkflow

from ..gui.utils.events import scheme_ewoks_events
from ..gui.utils.events import scheme_from_job_id
from ..gui.workflows.owscheme import ows_to_ewoks
from ..tasks import SaveWorkflow
from .examples.tasks import SumTaskTest

_WORKFLOW = {
    "graph": {"id": "save_workflow_test", "schema_version": "1.1"},
    "nodes": [
        {
            "id": "sum",
            "task_identifier": qualname(SumTaskTest),
            "task_type": "class",
            "default_inputs": [{"name": "a", "value": 1}],
        },
        {
            "id": "save",
            "task_identifier": qualname(SaveWorkflow),
            "task_type": "class",
        },
    ],
    "links": [],
}


def _default_inputs(graph, node_id) -> dict:
    return {
        item["name"]: item["value"]
        for item in graph.graph.nodes[node_id].get("default_inputs", list())
    }


def test_save_workflow_widget(tmp_path, orange_canvas_handler):
    orange_canvas_handler.load_graph(_WORKFLOW)

    # Change settings after loading: they must end up in the saved file
    sum_widget = orange_canvas_handler.widget_from_id("sum")
    sum_widget.update_default_inputs(a=5, b=7)

    filename = tmp_path / "saved.ows"
    save_widget = orange_canvas_handler.widget_from_id("save")
    assert isinstance(save_widget, OWSaveWorkflow)
    save_widget.update_default_inputs(filename=str(filename))
    future = save_widget.execute_ewoks_task()
    orange_canvas_handler.wait_widgets(timeout=10)

    assert future.succeeded(), future.task_exception()
    assert future.output_values() == {"filename": str(filename)}

    graph = ows_to_ewoks(str(filename))
    assert graph.graph.graph["id"] == "save_workflow_test"
    assert _default_inputs(graph, "sum") == {"a": 5, "b": 7}
    assert _default_inputs(graph, "save") == {"filename": str(filename)}

    # Saving again overwrites the file with the new settings
    sum_widget.set_default_input("a", 10)
    future = save_widget.execute_ewoks_task()
    orange_canvas_handler.wait_widgets(timeout=10)
    assert future.succeeded(), future.task_exception()
    graph = ows_to_ewoks(str(filename))
    assert _default_inputs(graph, "sum") == {"a": 10, "b": 7}


def test_save_workflow_task_in_worker_thread(tmp_path, orange_canvas_handler):
    orange_canvas_handler.load_graph(_WORKFLOW)
    scheme = orange_canvas_handler.scheme
    orange_canvas_handler.widget_from_id("sum").update_default_inputs(a=3)

    # The execution info a widget of this scheme passes to its task
    execinfo = scheme_ewoks_events(scheme)
    assert scheme_from_job_id(execinfo["job_id"]) is scheme

    filename = tmp_path / "saved.ows"
    task = SaveWorkflow(
        inputs={"filename": str(filename)}, execinfo=execinfo, node_id="save"
    )
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(task.execute)
        # The task waits for the GUI thread to serialize the scheme
        t0 = time.time()
        while not future.done():
            assert time.time() - t0 < 10, "timeout"
            orange_canvas_handler.process_events()
            time.sleep(0.01)
        future.result()

    assert task.get_output_values() == {"filename": str(filename)}
    graph = ows_to_ewoks(str(filename))
    assert _default_inputs(graph, "sum") == {"a": 3}


def test_save_workflow_task_without_canvas(tmp_path):
    filename = tmp_path / "saved.ows"
    with pytest.raises(RuntimeError, match="Orange canvas"):
        execute_graph(
            {
                "graph": {"id": "headless"},
                "nodes": [
                    {
                        "id": "save",
                        "task_identifier": qualname(SaveWorkflow),
                        "task_type": "class",
                        "default_inputs": [
                            {"name": "filename", "value": str(filename)}
                        ],
                    }
                ],
            }
        )
    assert not filename.exists()
