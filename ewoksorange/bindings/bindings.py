import os
import sys
from contextlib import contextmanager
from typing import Any, Iterator, Optional, List, Union

import ewokscore
from ewokscore.graph import TaskGraph
from . import owsconvert
from ..canvas.main import main as launchcanvas


__all__ = ["execute_graph", "load_graph", "save_graph", "convert_graph"]


@contextmanager
def ows_file_context(
    graph,
    inputs: Optional[List[dict]] = None,
    load_options: Optional[dict] = None,
    outputs: Optional[List[dict]] = None,
    merge_outputs: Optional[bool] = True,
    tmpdir: Optional[str] = None,
    **execute_options,
) -> Iterator[str]:
    """Yields an .ows file path (temporary file when not alread an .ows file)"""
    if outputs:
        raise ValueError("The Orange3 binding cannot return any results")
    if load_options is None:
        load_options = dict()
    representation = _get_representation(graph, options=load_options)
    if representation == "ows":
        ows_filename = graph
        if inputs or load_options or execute_options:
            # Already an .ows file but modify it before launching the GUI (default inputs, varinfo, execinfo)
            graph = owsconvert.ows_to_ewoks(ows_filename)
            basename = os.path.splitext(os.path.basename(ows_filename))[0]
            if tmpdir:
                tmp_filename = os.path.abspath(
                    os.path.join(str(tmpdir), f"{basename}_mod.ows")
                )
            else:
                tmp_filename = os.path.abspath(f"{basename}_mod.ows")
            try:
                owsconvert.ewoks_to_ows(
                    graph,
                    tmp_filename,
                    inputs=inputs,
                    **load_options,
                    **execute_options,
                )
                yield tmp_filename
            finally:
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
            owsconvert.ewoks_to_ows(
                graph, tmp_filename, inputs=inputs, **load_options, **execute_options
            )
            yield tmp_filename
        finally:
            os.remove(tmp_filename)


@ewokscore.execute_graph_decorator(binding="orange")
def execute_graph(graph, **kwargs) -> None:
    with ows_file_context(graph, **kwargs) as ows_filename:
        argv = [sys.argv[0], ows_filename]
        launchcanvas(argv=argv)


def load_graph(
    graph: Any,
    inputs: Optional[List[dict]] = None,
    preserve_ows_info: Optional[bool] = True,
    title_as_node_id: Optional[bool] = False,
    **load_options,
) -> TaskGraph:
    representation = _get_representation(graph, options=load_options)
    if representation == "ows":
        load_options.pop("representation", None)
        return owsconvert.ows_to_ewoks(
            graph,
            inputs=inputs,
            preserve_ows_info=preserve_ows_info,
            title_as_node_id=title_as_node_id,
            **load_options,
        )
    else:
        return ewokscore.load_graph(graph, inputs=inputs, **load_options)


def save_graph(graph: TaskGraph, destination, **save_options) -> Union[str, dict]:
    representation = _get_representation(destination, options=save_options)
    if representation == "ows":
        owsconvert.ewoks_to_ows(graph, destination, **save_options)
        return destination
    else:
        return graph.dump(destination, **save_options)


def convert_graph(
    source,
    destination,
    inputs: Optional[List[dict]] = None,
    load_options: Optional[dict] = None,
    save_options: Optional[dict] = None,
) -> Union[str, dict]:
    if load_options is None:
        load_options = dict()
    if save_options is None:
        save_options = dict()
    graph = load_graph(source, inputs=inputs, **load_options)
    return save_graph(graph, destination, **save_options)


def _get_representation(graph: Any, options: Optional[dict] = None):
    representation = None
    if options:
        representation = options.get("representation")
    if (
        representation is None
        and isinstance(graph, str)
        and graph.lower().endswith(".ows")
    ):
        representation = "ows"
    return representation
