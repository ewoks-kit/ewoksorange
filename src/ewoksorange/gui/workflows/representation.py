import os
from contextlib import contextmanager
from typing import Any
from typing import Generator
from typing import List
from typing import Optional
from typing import Union

from ewokscore.graph.serialize import GraphRepresentation

from .owscheme import ewoks_to_ows
from .owscheme import ows_to_ewoks


def get_representation(
    graph: Any, representation: Optional[Union[GraphRepresentation, str]] = None
) -> Optional[str]:
    if (
        representation is None
        and isinstance(graph, str)
        and graph.lower().endswith(".ows")
    ):
        representation = "ows"
    return representation


@contextmanager
def ows_file_context(
    graph,
    inputs: Optional[List[dict]] = None,
    load_options: Optional[dict] = None,
    varinfo: Optional[dict] = None,
    execinfo: Optional[dict] = None,
    task_options: Optional[dict] = None,
    error_on_duplicates: bool = True,
    tmpdir: Optional[str] = None,
) -> Generator[str, None, None]:
    """Yields an .ows file path (temporary file when not alread an .ows file)"""
    if load_options is None:
        load_options = dict()
    representation = get_representation(
        graph, representation=load_options.get("representation")
    )
    if representation == "ows":
        ows_filename = graph
        if inputs or varinfo or execinfo or task_options:
            # Already an .ows file but we need to inject data so that
            # `OWEwoksBaseWidget` can retrieve it in `_get_task_arguments`
            # to instantiate an Ewoks tasks.
            # See `OwsNodeWrapper` on how this information gets passed.
            graph = ows_to_ewoks(ows_filename, **load_options)
            basename = os.path.splitext(os.path.basename(ows_filename))[0]
            if tmpdir:
                tmp_filename = os.path.abspath(
                    os.path.join(str(tmpdir), f"{basename}_mod.ows")
                )
            else:
                tmp_filename = os.path.abspath(f"{basename}_mod.ows")
            try:
                ewoks_to_ows(
                    graph,
                    tmp_filename,
                    inputs=inputs,
                    varinfo=varinfo,
                    execinfo=execinfo,
                    task_options=task_options,
                    error_on_duplicates=error_on_duplicates,
                )
                yield tmp_filename
            finally:
                if os.path.exists(tmp_filename):
                    os.remove(tmp_filename)
        else:
            # Already an .ows file
            yield ows_filename
    else:
        # Convert to an .ows file before launching the GUI
        if tmpdir:
            tmp_filename = os.path.abspath(
                os.path.join(str(tmpdir), "ewoks_workflow_tmp.ows")
            )
        else:
            tmp_filename = os.path.abspath("ewoks_workflow_tmp.ows")
        try:
            ewoks_to_ows(
                graph,
                tmp_filename,
                inputs=inputs,
                varinfo=varinfo,
                execinfo=execinfo,
                task_options=task_options,
                error_on_duplicates=error_on_duplicates,
                **load_options,
            )
            yield tmp_filename
        finally:
            if os.path.exists(tmp_filename):
                os.remove(tmp_filename)
