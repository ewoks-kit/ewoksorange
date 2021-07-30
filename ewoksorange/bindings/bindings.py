import os
import sys
import tempfile
from Orange.canvas.__main__ import main as launchcanvas
from ewokscore import load_graph
from .. import owsconvert


def execute_graph(graph, representation=None, varinfo=None):
    ewoksgraph = load_graph(source=graph, representation=representation)
    if ewoksgraph.is_cyclic:
        raise RuntimeError("Orange can only execute DAGs")
    if ewoksgraph.has_conditional_links:
        raise RuntimeError("Orange cannot handle conditional links")

    # We do not have a mapping between OWS and the runtime representation.
    # So map to a (temporary) persistent representation first.
    with tempfile.TemporaryDirectory() as tmpdirname:
        filename = os.path.join(tmpdirname, "ewokstaskgraph.ows")
        owsconvert.ewoks_to_ows(ewoksgraph, filename, varinfo=varinfo)
        argv = [sys.argv[0], filename]
        launchcanvas(argv=argv)
