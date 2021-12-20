import os
import sys
import logging
import tempfile
import pytest

from ewokscore.tests.examples.graphs import get_graph
from ewokscore.tests.utils import assert_taskgraph_result
from ewokscore import load_graph
from ewoksorange.bindings import ewoks_to_ows

logging.getLogger("orange").setLevel(logging.DEBUG)
logging.getLogger("orange").addHandler(logging.StreamHandler(sys.stdout))
logging.getLogger("ewoksorange").setLevel(logging.DEBUG)
logging.getLogger("ewoksorange").addHandler(logging.StreamHandler(sys.stdout))


@pytest.mark.parametrize("graph_name", ["acyclic1", "cyclic1"])
def test_execute_graph(graph_name, tmpdir, ewoks_orange_canvas):
    """Test graph execution like the Orange canvas would do it"""
    graph, expected = get_graph(graph_name)
    ewoksgraph = load_graph(graph)
    varinfo = {"root_uri": str(tmpdir)}
    no_explicit_datamapping = any(
        not link_attrs.get("data_mapping")
        for link_attrs in ewoksgraph.graph.edges.values()
    )
    if (
        ewoksgraph.is_cyclic
        or ewoksgraph.has_conditional_links
        or no_explicit_datamapping
    ):
        pytest.skip("graph not supported by orange")
    else:
        with tempfile.TemporaryDirectory() as tmpdirname:
            filename = os.path.join(tmpdirname, graph_name + ".ows")
            ewoks_to_ows(
                ewoksgraph, filename, varinfo=varinfo, error_on_duplicates=False
            )
            ewoks_orange_canvas.load_ows(filename)
        ewoks_orange_canvas.wait_widgets(timeout=10)

        assert_taskgraph_result(ewoksgraph, expected, varinfo=varinfo)
