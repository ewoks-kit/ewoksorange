import pytest
from ewokscore.tests.examples.graphs import graph_names
from ewokscore.tests.examples.graphs import get_graph
from ewokscore.tests.test_examples import assert_convert_graph
from ewokscore.tests.utils.results import assert_execute_graph_tasks
from ewokscore import load_graph
from ewoksorange import convert_graph
from ewoksorange import graph_is_supported


@pytest.mark.parametrize("graph_name", graph_names())
def test_execute_graph(graph_name, tmpdir, ewoks_orange_canvas):
    """Test graph execution like the Orange canvas would do it"""
    graph, expected = get_graph(graph_name)
    ewoksgraph = load_graph(graph)
    varinfo = {"root_uri": str(tmpdir)}
    if not graph_is_supported(ewoksgraph):
        pytest.skip("graph not supported by orange")

    ewoks_orange_canvas.load_graph(
        ewoksgraph, varinfo=varinfo, error_on_duplicates=False, tmpdir=tmpdir
    )
    ewoks_orange_canvas.start_workflow()
    ewoks_orange_canvas.wait_widgets(timeout=10)

    assert_execute_graph_tasks(ewoksgraph, dict(), expected, varinfo=varinfo)


@pytest.mark.parametrize("graph_name", graph_names())
def test_convert_graph(graph_name, tmpdir):
    graph, _ = get_graph(graph_name)
    ewoksgraph = load_graph(graph)
    for node_id, node_attrs in ewoksgraph.graph.nodes.items():
        node_attrs["label"] = node_id

    representations = [
        (
            {
                "representation": "ows",
                "title_as_node_id": True,
                "preserve_ows_info": False,
            },
            {"representation": "ows"},
            "ows",
        )
    ]
    if graph_is_supported(ewoksgraph):
        assert_convert_graph(
            convert_graph, ewoksgraph, tmpdir, representations=representations
        )
    else:
        with pytest.raises(RuntimeError):
            assert_convert_graph(
                convert_graph, ewoksgraph, tmpdir, representations=representations
            )
