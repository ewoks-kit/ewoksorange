import sys
import logging
import pytest
from ewoksorange import job
from ewokscore.tests.examples import graphs
from ewokscore.tests.utils import assert_taskgraph_result

logging.getLogger("orange").setLevel(logging.DEBUG)
logging.getLogger("orange").addHandler(logging.StreamHandler(sys.stdout))
logging.getLogger("ewoksorange").setLevel(logging.DEBUG)
logging.getLogger("ewoksorange").addHandler(logging.StreamHandler(sys.stdout))


@pytest.mark.skip("TODO: hashes are different due to static input")
def test_job(tmpdir):
    varinfo = {"root_uri": str(tmpdir)}
    graph, expected = graphs.acyclic_graph1()
    job(graph, varinfo=varinfo)
    assert_taskgraph_result(graph, expected, varinfo)
