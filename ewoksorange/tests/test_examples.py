import sys
import logging
import pytest
from ewoksorange import execute_graph
from ewokscore.tests.examples.graphs import get_graph
from ewokscore.tests.utils import assert_taskgraph_result
from ewokscore import load_graph

logging.getLogger("orange").setLevel(logging.DEBUG)
logging.getLogger("orange").addHandler(logging.StreamHandler(sys.stdout))
logging.getLogger("ewoksorange").setLevel(logging.DEBUG)
logging.getLogger("ewoksorange").addHandler(logging.StreamHandler(sys.stdout))


@pytest.mark.parametrize("graph_name", ["acyclic1", "cyclic1"])
def test_execute_graph(graph_name, tmpdir, register_ewoks_example_addons):
    graph, expected = get_graph(graph_name)
    ewoksgraph = load_graph(graph)
    varinfo = {"root_uri": str(tmpdir)}
    if ewoksgraph.is_cyclic or ewoksgraph.has_conditional_links:
        with pytest.raises(RuntimeError):
            execute_graph(graph, varinfo=varinfo)
    else:
        pytest.skip("Not sure how to close the Qt app when everything is done")
        execute_graph(graph, varinfo=varinfo)
        assert_taskgraph_result(ewoksgraph, expected, varinfo=varinfo)
