import pytest
from ewokscore import execute_graph

from ..gui.workflows.owscheme import ows_to_ewoks
from ..orange_version import ORANGE_VERSION

try:
    from importlib.resources import files as resource_files
except ImportError:
    from importlib_resources import files as resource_files


def test_sumtask_tutorial_with_qt(ewoks_orange_canvas):
    from orangecontrib.ewokstest import tutorials

    filename = resource_files(tutorials).joinpath("sumtask_tutorial.ows")
    assert_sumtask_tutorial_with_qt(ewoks_orange_canvas, filename)


def test_sumtask_tutorial_without_qt(qtapp):
    from orangecontrib.ewokstest import tutorials

    filename = resource_files(tutorials).joinpath("sumtask_tutorial.ows")
    assert_sumtask_tutorial_without_qt(filename)


def test_list_operations_with_qt(ewoks_orange_canvas):
    from orangecontrib.ewokstest import tutorials

    filename = resource_files(tutorials).joinpath("sumlist_tutorial.ows")
    assert_sumlist_tutorial_with_qt(ewoks_orange_canvas, filename)


def test_list_operations_without_qt(qtapp):
    from orangecontrib.ewokstest import tutorials

    filename = resource_files(tutorials).joinpath("sumlist_tutorial.ows")
    assert_sumlist_tutorial_without_qt(filename)


def test_mixed_tutorial_with_qt(ewoks_orange_canvas):
    from orangecontrib.ewokstest import tutorials

    if ORANGE_VERSION == ORANGE_VERSION.latest_orange:
        workflow = "mixed_tutorial.ows"
    elif ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
        workflow = "mixed_tutorial_oasys.ows"
    else:
        pytest.skip("Requires the Orange3 or Oasys1 python script widget")

    filename = resource_files(tutorials).joinpath(workflow)
    assert_mixed_tutorial_with_qt(ewoks_orange_canvas, filename)


def test_mixed_tutorial_without_qt(qtapp):
    from orangecontrib.ewokstest import tutorials

    if ORANGE_VERSION == ORANGE_VERSION.latest_orange:
        workflow = "mixed_tutorial.ows"
    elif ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
        workflow = "mixed_tutorial_oasys.ows"
    else:
        pytest.skip("Requires the Orange3 or Oasys1 python script widget")

    filename = resource_files(tutorials).joinpath(workflow)
    assert_mixed_tutorial_without_qt(filename)


def assert_sumtask_tutorial_with_qt(ewoks_orange_canvas, filename):
    """Execute workflow using the Qt widgets and signals"""
    ewoks_orange_canvas.load_ows(str(filename))
    ewoks_orange_canvas.start_workflow()
    ewoks_orange_canvas.wait_widgets(timeout=10)
    widgets = list(ewoks_orange_canvas.widgets_from_name("task6"))
    results = widgets[0].get_task_output_values()
    assert results == {"result": 16}

    ewoks_orange_canvas.load_ows(str(filename))
    ewoks_orange_canvas.set_input_values(
        [{"label": "task1", "name": "b", "value": "wrongtype"}]
    )
    ewoks_orange_canvas.start_workflow()
    with pytest.raises(TypeError):
        # Note: we get the original error, not "RuntimeError: Task 'task1' failed"
        ewoks_orange_canvas.wait_widgets(timeout=10)


def assert_sumtask_tutorial_without_qt(filename):
    """Execute workflow after converting it to an ewoks workflow"""
    graph = ows_to_ewoks(filename)
    results = execute_graph(graph, output_tasks=True)
    assert results["5"].get_output_values() == {"result": 16}


def assert_sumlist_tutorial_with_qt(ewoks_orange_canvas, filename):
    """Execute workflow using the Qt widgets and signals"""
    ewoks_orange_canvas.load_ows(str(filename))

    # Remove artificial delay for this test
    for widget in ewoks_orange_canvas.iter_widgets():
        if "delay" in widget.get_default_input_names():
            widget.update_default_inputs(delay=0)

    ewoks_orange_canvas.start_workflow()
    ewoks_orange_canvas.wait_widgets(timeout=10)

    wgenerator = list(ewoks_orange_canvas.widgets_from_name("List generator"))[0]
    results = wgenerator.get_task_output_values()
    listsum = sum(results["list"])

    widgets = list(ewoks_orange_canvas.widgets_from_name("Print list sum"))
    widgets += list(ewoks_orange_canvas.widgets_from_name("Print list sum (1)"))
    widgets += list(ewoks_orange_canvas.widgets_from_name("Print list sum (2)"))
    for w in widgets:
        results = {name: var.value for name, var in w.get_task_inputs().items()}
        assert results == {"sum": listsum}


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


def assert_mixed_tutorial_with_qt(ewoks_orange_canvas, filename):
    """Execute workflow using the Qt widgets and signals"""
    ewoks_orange_canvas.load_ows(str(filename))
    ewoks_orange_canvas.start_workflow()
    ewoks_orange_canvas.wait_widgets(timeout=10)
    widget = ewoks_orange_canvas.widget_from_id("2")
    results = widget.get_task_output_values()
    assert results == {"result": 3}


def assert_mixed_tutorial_without_qt(filename):
    """Execute workflow after converting it to an ewoks workflow"""
    graph = ows_to_ewoks(filename)
    tasks = execute_graph(graph, output_tasks=True)
    results = tasks["2"].get_output_values()
    assert results == {"result": 3}
