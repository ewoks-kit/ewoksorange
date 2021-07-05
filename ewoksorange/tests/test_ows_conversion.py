from importlib import resources
from ewoksorange import owsconvert
from ewokscore import load_graph
from ewokscore.tests.examples import graphs


def test_ows_to_ewoks(tmpdir, register_ewoks_example_addon):
    from orangecontrib.evaluate.submodule import tutorials

    with resources.path(tutorials, "sumtask_tutorial2.ows") as filename:
        ewoksgraph = owsconvert.ows_to_ewoks(str(filename))

    destination = str(tmpdir / "ewoksgraph.ows")
    owsconvert.ewoks_to_ows(ewoksgraph, destination)
    ewoksgraph2 = owsconvert.ows_to_ewoks(destination)
    assert ewoksgraph == ewoksgraph2


def test_ewoks_to_ows(tmpdir):
    graph, _ = graphs.acyclic_graph1()
    ewoksgraph = load_graph(graph)

    destination = str(tmpdir / "ewoksgraph2.ows")
    owsconvert.ewoks_to_ows(ewoksgraph, destination)

    ewoksgraph2 = owsconvert.ows_to_ewoks(destination)
    assert ewoksgraph.dump() == ewoksgraph2.dump()
