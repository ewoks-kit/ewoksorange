import os
import sys
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Iterator, Optional, List, Union

import ewokscore
from ewokscore.graph import TaskGraph
from ewokscore.graph.serialize import GraphRepresentation

from . import owsconvert
from ..canvas.main import main as launchcanvas


__all__ = ["execute_graph", "load_graph", "save_graph", "convert_graph"]


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
) -> Iterator[str]:
    """Yields an .ows file path (temporary file when not alread an .ows file)"""
    if load_options is None:
        load_options = dict()
    representation = _get_representation(
        graph, representation=load_options.get("representation")
    )
    if representation == "ows":
        ows_filename = graph
        if inputs or varinfo or execinfo or task_options:
            # Already an .ows file but we need to inject data so that
            # `OWEwoksBaseWidget` can retrieve it in `_get_task_arguments`
            # to instantiate an Ewoks tasks.
            # See `OwsNodeWrapper` on how this information gets passed.
            graph = owsconvert.ows_to_ewoks(ows_filename, **load_options)
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
            owsconvert.ewoks_to_ows(
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


@ewokscore.execute_graph_decorator(engine="orange")
def execute_graph(
    graph: Any,
    inputs: Optional[List[dict]] = None,
    load_options: Optional[dict] = None,
    varinfo: Optional[dict] = None,
    execinfo: Optional[dict] = None,
    task_options: Optional[dict] = None,
    outputs: Optional[List[dict]] = None,
    merge_outputs: Optional[bool] = True,
    error_on_duplicates: bool = True,
    tmpdir: Optional[str] = None,
) -> None:
    if outputs:
        raise ValueError("The Orange3 binding cannot return any results")
    with ows_file_context(
        graph,
        inputs=inputs,
        load_options=load_options,
        varinfo=varinfo,
        execinfo=execinfo,
        task_options=task_options,
        error_on_duplicates=error_on_duplicates,
        tmpdir=tmpdir,
    ) as ows_filename:
        argv = [sys.argv[0], ows_filename]
        launchcanvas(argv=argv)


def load_graph(
    graph: Any,
    inputs: Optional[List[dict]] = None,
    representation: Optional[Union[GraphRepresentation, str]] = None,
    root_dir: Optional[Union[str, Path]] = None,
    root_module: Optional[str] = None,
    preserve_ows_info: Optional[bool] = True,
    title_as_node_id: Optional[bool] = False,
) -> TaskGraph:
    representation = _get_representation(graph, representation=representation)
    if representation == "ows":
        return owsconvert.ows_to_ewoks(
            graph,
            inputs=inputs,
            root_dir=root_dir,
            root_module=root_module,
            preserve_ows_info=preserve_ows_info,
            title_as_node_id=title_as_node_id,
        )
    else:
        return ewokscore.load_graph(
            graph,
            inputs=inputs,
            representation=representation,
            root_dir=root_dir,
            root_module=root_module,
        )


def save_graph(
    graph: TaskGraph,
    destination,
    representation: Optional[Union[GraphRepresentation, str]] = None,
    **save_options,
) -> Union[str, dict]:
    representation = _get_representation(destination, representation=representation)
    if representation == "ows":
        owsconvert.ewoks_to_ows(graph, destination, **save_options)
        return destination
    else:
        return graph.dump(destination, representation=representation, **save_options)


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


def _get_representation(
    graph: Any, representation: Optional[Union[GraphRepresentation, str]] = None
) -> Optional[str]:
    if (
        representation is None
        and isinstance(graph, str)
        and graph.lower().endswith(".ows")
    ):
        representation = "ows"
    return representation
