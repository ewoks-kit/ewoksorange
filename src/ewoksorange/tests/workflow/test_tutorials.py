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
    elif ORANGE_VERSION == ORANGE_VERSION.latest_oasys:
        workflow = "mixed_tutorial_oasys2.ows"
    else:
        pytest.skip("Requires the Orange3 or OASYS2 python script widget")

    filename = resource_files(tutorials).joinpath(workflow)
    assert_mixed_tutorial_with_qt(filename)


def test_mixed_tutorial_without_qt(ewoksorange_qtapp):
    from orangecontrib.ewokstest import tutorials

    if ORANGE_VERSION == ORANGE_VERSION.latest_orange:
        workflow = "mixed_tutorial.ows"
    elif ORANGE_VERSION == ORANGE_VERSION.latest_oasys:
        workflow = "mixed_tutorial_oasys2.ows"
    else:
        pytest.skip("Requires the Orange3 or OASYS2 python script widget")

    filename = resource_files(tutorials).joinpath(workflow)
    assert_mixed_tutorial_without_qt(filename)


def _sumtask_delay_inputs():
    """Remove the artificial delay of the "SumTaskTest" task for this test."""
    return [{"task_identifier": "SumTaskTest", "name": "delay", "value": 0}]


def assert_sumtask_tutorial_with_qt(filename):
    """Execute workflow using the Qt widgets and signals"""
    results = execute_graph_orange(
        str(filename),
        inputs=_sumtask_delay_inputs(),
        outputs=[{"label": "task6"}],
        no_gui=True,
        timeout=10,
    )
    assert results == {"result": 16}

    with pytest.raises(TypeError):
        # Note: we get the original error, not "RuntimeError: Task 'task1' failed"
        execute_graph_orange(
            str(filename),
            inputs=_sumtask_delay_inputs()
            + [{"label": "task1", "name": "b", "value": "wrongtype"}],
            no_gui=True,
            timeout=10,
        )


def assert_sumtask_tutorial_without_qt(filename):
    """Execute workflow after converting it to an ewoks workflow"""
    graph = ows_to_ewoks(filename)
    results = execute_graph(graph, inputs=_sumtask_delay_inputs(), output_tasks=True)
    assert results["5"].get_output_values() == {"result": 16}


def _sumlist_delay_inputs():
    """Remove the artificial delay of the "SumList*" tasks for this test."""
    return [
        {"task_identifier": s, "name": "delay", "value": 0}
        for s in ("SumList", "SumList2", "SumList3")
    ]


def assert_sumlist_tutorial_with_qt(handler, filename):
    """Execute workflow directly."""
    execute_graph_orange(
        str(filename),
        inputs=_sumlist_delay_inputs(),
        no_gui=True,
        timeout=10,
        orange_canvas_handler=handler,
    )

    with pytest.warns(DeprecationWarning):
        output_values = handler.widget_from_id("0").get_task_output_values()
    listsum = sum(output_values["list"])
    for i in [4, 5, 6]:
        assert handler.widget_from_id(str(i)).get_task_input_values() == {
            "sum": listsum
        }


def assert_sumlist_tutorial_without_qt(filename):
    """Execute workflow after converting it to an ewoks workflow."""
    graph = ows_to_ewoks(filename)
    results = execute_graph(graph, inputs=_sumlist_delay_inputs(), output_tasks=True)
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
