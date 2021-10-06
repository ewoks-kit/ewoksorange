from ewoksorange.bindings import ows_to_ewoks

try:
    from importlib import resources
except ImportError:
    import importlib_resources as resources


def test_sumtask_tutorial1(ewoks_orange_canvas):
    from orangecontrib.ewoks_example_category import tutorials

    with resources.path(tutorials, "sumtask_tutorial1.ows") as filename:
        assert_sumtask_tutorial(ewoks_orange_canvas, filename)


def test_sumtask_tutorial1_without_qt(register_ewoks_example_addons):
    from orangecontrib.ewoks_example_category import tutorials

    with resources.path(tutorials, "sumtask_tutorial1.ows") as filename:
        assert_sumtask_tutorial_without_qt(filename)


def test_sumtask_tutorial2(ewoks_orange_canvas):
    from orangecontrib.evaluate.ewoks_example_submodule import tutorials

    with resources.path(tutorials, "sumtask_tutorial2.ows") as filename:
        assert_sumtask_tutorial(ewoks_orange_canvas, filename)


def test_sumtask_tutorial2_without_qt(ewoks_orange_canvas):
    from orangecontrib.evaluate.ewoks_example_submodule import tutorials

    with resources.path(tutorials, "sumtask_tutorial2.ows") as filename:
        assert_sumtask_tutorial_without_qt(filename)


def test_sumtask_tutorial3(ewoks_orange_canvas):
    from orangecontrib.ewoks_example_supercategory.ewoks_example_subcategory import (
        tutorials,
    )

    with resources.path(tutorials, "sumtask_tutorial3.ows") as filename:
        assert_sumtask_tutorial(ewoks_orange_canvas, filename)


def test_sumtask_tutorial3_without_qt(ewoks_orange_canvas):
    from orangecontrib.ewoks_example_supercategory.ewoks_example_subcategory import (
        tutorials,
    )

    with resources.path(tutorials, "sumtask_tutorial3.ows") as filename:
        assert_sumtask_tutorial_without_qt(filename)


def test_list_operations(ewoks_orange_canvas):
    from orangecontrib.list_operations import tutorials

    with resources.path(tutorials, "sumlist_tutorial.ows") as filename:
        assert_sumlist_tutorial(ewoks_orange_canvas, filename)


def test_list_operations_without_qt(ewoks_orange_canvas):
    from orangecontrib.list_operations import tutorials

    with resources.path(tutorials, "sumlist_tutorial.ows") as filename:
        assert_sumlist_tutorial_without_qt(filename)


def assert_sumtask_tutorial(ewoks_orange_canvas, filename):
    """Execute workflow using the Qt widgets and signals"""
    ewoks_orange_canvas.load_ows(str(filename))
    ewoks_orange_canvas.wait_widgets()
    widgets = list(ewoks_orange_canvas.widgets_from_name("task6"))
    results = widgets[0].task_output_values
    assert results == {"result": 16}


def assert_sumtask_tutorial_without_qt(filename):
    """Execute workflow after converting it to an ewoks workflow"""
    graph = ows_to_ewoks(filename)
    results = graph.execute()
    assert results["5"].output_values == {"result": 16}


def assert_sumlist_tutorial(ewoks_orange_canvas, filename):
    """Execute workflow using the Qt widgets and signals"""
    ewoks_orange_canvas.load_ows(str(filename))
    wgenerator = list(ewoks_orange_canvas.widgets_from_name("List generator"))[0]
    wgenerator.defaultInputsHaveChanged()
    results = wgenerator.task_output_values
    listsum = sum(results["list"])

    def widget_is_ready(widget):
        return bool(widget.task_inputs)

    ewoks_orange_canvas.wait_widgets(widget_is_ready=widget_is_ready)

    widgets = list(ewoks_orange_canvas.widgets_from_name("Print list sum"))
    widgets = list(ewoks_orange_canvas.widgets_from_name("Print list sum (1)"))
    widgets = list(ewoks_orange_canvas.widgets_from_name("Print list sum (2)"))
    for w in widgets:
        results = {name: var.value for name, var in w.task_inputs.items()}
        assert results == {"sum": listsum}


def assert_sumlist_tutorial_without_qt(filename):
    """Execute workflow after converting it to an ewoks workflow"""
    graph = ows_to_ewoks(filename)
    results = graph.execute()
    listsum = sum(results["0"].output_values["list"])
    for i in [4, 5, 6]:
        assert results[str(i)].input_values == {"sum": listsum}
