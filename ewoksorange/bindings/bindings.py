import os
import sys
import tempfile
from typing import Optional, List

from ewokscore.events import job_decorator as execute_graph_decorator
from .owsconvert import ewoks_to_ows
from ..canvas.__main__ import main as launchcanvas


__all__ = ["execute_graph"]


@execute_graph_decorator(binding="orange")
def execute_graph(
    graph,
    inputs: Optional[List[dict]] = None,
    load_options: Optional[dict] = None,
    **execute_options
):
    if isinstance(graph, str) and graph.lower().endswith(".ows"):
        argv = [sys.argv[0], graph]
        launchcanvas(argv=argv)
    else:
        # We do not have a mapping between OWS and the runtime representation.
        # So map to a (temporary) persistent representation first.
        with tempfile.TemporaryDirectory(prefix="ewoksorange") as tmpdirname:
            filename = os.path.join(tmpdirname, "ewokstaskgraph.ows")
            if load_options is None:
                load_options = dict()
            # Note: execute options are saved in the temporary file
            ewoks_to_ows(
                graph, filename, inputs=inputs, **load_options, **execute_options
            )
            argv = [sys.argv[0], filename]
            launchcanvas(argv=argv)
