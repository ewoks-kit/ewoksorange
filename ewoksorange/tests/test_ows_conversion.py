try:
    from importlib import resources
except ImportError:
    import importlib_resources as resources
import pytest
from ewoksorange import owsconvert
from ewokscore import load_graph
from ewokscore.tests.examples.graphs import graph_names
from ewokscore.tests.examples.graphs import get_graph


def test_ows_to_ewoks(tmpdir, register_ewoks_example_addon):
    from orangecontrib.evaluate.submodule import tutorials

    with resources.path(tutorials, "sumtask_tutorial2.ows") as filename:
        ewoksgraph = owsconvert.ows_to_ewoks(str(filename))

    destination = str(tmpdir / "ewoksgraph.ows")
    owsconvert.ewoks_to_ows(ewoksgraph, destination)
    ewoksgraph2 = owsconvert.ows_to_ewoks(destination)
    assert ewoksgraph == ewoksgraph2


@pytest.mark.parametrize("graph_name", graph_names())
def test_ewoks_to_ows(graph_name, tmpdir):
    graph, _ = get_graph(graph_name)
    ewoksgraph = load_graph(graph)

    destination = str(tmpdir / "ewoksgraph2.ows")
    if ewoksgraph.is_cyclic or ewoksgraph.has_conditional_links:
        with pytest.raises(RuntimeError):
            owsconvert.ewoks_to_ows(ewoksgraph, destination)
        return
    owsconvert.ewoks_to_ows(ewoksgraph, destination)

    ewoksgraph2 = owsconvert.ows_to_ewoks(destination)
    assert ewoksgraph.dump() == ewoksgraph2.dump()
