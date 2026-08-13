import warnings

import pytest
from ewokscore.bindings import execute_graph
from ewoksutils.exceptions import TaskInputWarning

from ...bindings import execute_graph as execute_graph_orange
from ...gui.workflows.owscheme import ows_to_ewoks
from ...orange_version import ORANGE_VERSION

try:
    from importlib.resources import files as resource_files
except ImportError:
    from importlib_resources import files as resource_files


def test_sumtask_tutorial_with_qt(ewoksorange_qtapp):
    from orangecontrib.ewokstest import tutorials

    filename = resource_files(tutorials).joinpath("sumtask_tutorial.ows")
    assert_sumtask_tutorial_with_qt(filename)


def test_sumtask_tutorial_without_qt(ewoksorange_qtapp):
    from orangecontrib.ewokstest import tutorials

    filename = resource_files(tutorials).joinpath("sumtask_tutorial.ows")
    assert_sumtask_tutorial_without_qt(filename)


def test_list_operations_with_qt(orange_canvas_handler):
    from orangecontrib.ewokstest import tutorials

    filename = resource_files(tutorials).joinpath("sumlist_tutorial.ows")
    assert_sumlist_tutorial_with_qt(orange_canvas_handler, filename)


def test_list_operations_without_qt(ewoksorange_qtapp):
    from orangecontrib.ewokstest import tutorials

    filename = resource_files(tutorials).joinpath("sumlist_tutorial.ows")
    assert_sumlist_tutorial_without_qt(filename)


def test_mixed_tutorial_with_qt(ewoksorange_qtapp):
    from orangecontrib.ewokstest import tutorials

    if ORANGE_VERSION == ORANGE_VERSION.latest_orange:
        workflow = "mixed_tutorial.ows"
    elif ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
        workflow = "mixed_tutorial_oasys.ows"
    else:
        pytest.skip("Requires the Orange3 or Oasys1 python script widget")

    filename = resource_files(tutorials).joinpath(workflow)
    assert_mixed_tutorial_with_qt(filename)


def test_mixed_tutorial_without_qt(ewoksorange_qtapp):
    from orangecontrib.ewokstest import tutorials

    if ORANGE_VERSION == ORANGE_VERSION.latest_orange:
        workflow = "mixed_tutorial.ows"
    elif ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
        workflow = "mixed_tutorial_oasys.ows"
    else:
        pytest.skip("Requires the Orange3 or Oasys1 python script widget")

    filename = resource_files(tutorials).joinpath(workflow)
    assert_mixed_tutorial_without_qt(filename)


def assert_sumtask_tutorial_with_qt(filename):
    """Execute workflow using the Qt widgets and signals"""
    results = execute_graph_orange(
        str(filename), outputs=[{"label": "task6"}], no_gui=True, timeout=10
    )
    assert results == {"result": 16}

    with pytest.raises(TypeError):
        # Note: we get the original error, not "RuntimeError: Task 'task1' failed"
        execute_graph_orange(
            str(filename),
            inputs=[{"label": "task1", "name": "b", "value": "wrongtype"}],
            no_gui=True,
            timeout=10,
        )


def assert_sumtask_tutorial_without_qt(filename):
    """Execute workflow after converting it to an ewoks workflow"""
    graph = ows_to_ewoks(filename)
    results = execute_graph(graph, output_tasks=True)
    assert results["5"].get_output_values() == {"result": 16}


def assert_sumlist_tutorial_with_qt(handler, filename):
    """Execute workflow using the Qt widgets and signals.

    Uses the `OrangeCanvasHandler` directly (rather than
    `execute_graph(..., no_gui=True)`) since it inspects the resolved *input*
    values of "Print list sum" widgets, which have no Ewoks task output to
    check against.
    """
    handler.load_ows(str(filename))

    # Remove artificial delay for this test
    for widget in handler.iter_widgets():
        if "delay" in widget.get_default_input_names():
            widget.update_default_inputs(delay=0)

    handler.start_workflow()
    handler.wait_widgets(timeout=10)

    listsum = sum(handler.widget_from_id("0").get_task_output_values()["list"])
    for i in [4, 5, 6]:
        assert handler.widget_from_id(str(i)).get_task_input_values() == {
            "sum": listsum
        }


def assert_sumlist_tutorial_without_qt(filename):
    """Execute workflow after converting it to an ewoks workflow"""
    graph = ows_to_ewoks(filename)

    # Remove artificial delay for this test
    for attrs in graph.graph.nodes.values():
        for adict in attrs.get("default_inputs", list()):
            if adict["name"] == "delay":
                adict["value"] = 0

    results = execute_graph(graph, output_tasks=True)
    listsum = sum(results["0"].get_output_values()["list"])
    for i in [4, 5, 6]:
        assert results[str(i)].get_input_values() == {"sum": listsum}


def assert_mixed_tutorial_with_qt(filename):
    """Execute workflow using the Qt widgets and signals"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", TaskInputWarning)
        results = execute_graph_orange(
            str(filename),
            outputs=[{"id": "2"}],
            no_gui=True,
            timeout=10,
        )
    assert results == {"result": 3}


def assert_mixed_tutorial_without_qt(filename):
    """Execute workflow after converting it to an ewoks workflow"""
    graph = ows_to_ewoks(filename)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", TaskInputWarning)
        tasks = execute_graph(graph, output_tasks=True)

    results = tasks["2"].get_output_values()
    assert results == {"result": 3}
