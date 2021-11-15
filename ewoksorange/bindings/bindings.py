import os
import sys
import tempfile
from typing import Optional

from ewokscore import load_graph
from .owsconvert import ewoks_to_ows
from ..canvas.__main__ import main as launchcanvas


__all__ = ["execute_graph"]


def execute_graph(graph, load_options: Optional[dict] = None, **execute_options):
    if load_options is None:
        load_options = dict()
    ewoksgraph = load_graph(source=graph, **load_options)
    if ewoksgraph.is_cyclic:
        raise RuntimeError("Orange can only execute DAGs")
    if ewoksgraph.has_conditional_links:
        raise RuntimeError("Orange cannot handle conditional links")

    # We do not have a mapping between OWS and the runtime representation.
    # So map to a (temporary) persistent representation first.
    with tempfile.TemporaryDirectory() as tmpdirname:
        filename = os.path.join(tmpdirname, "ewokstaskgraph.ows")
        ewoks_to_ows(ewoksgraph, filename, **execute_options)
        argv = [sys.argv[0], filename]
        launchcanvas(argv=argv)
