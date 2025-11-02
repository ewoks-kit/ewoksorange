import importlib
import sys
import warnings
from pathlib import Path
from typing import Any
from typing import List
from typing import Optional
from typing import Union

import ewokscore
from ewokscore.graph import TaskGraph
from ewokscore.graph.serialize import GraphRepresentation

from ..gui.canvas.main import main as launchcanvas
from ..gui.workflows import owscheme
from ..gui.workflows.representation import get_representation
from ..gui.workflows.representation import ows_file_context


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
    representation = get_representation(graph, representation=representation)
    if representation == "ows":
        return owscheme.ows_to_ewoks(
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
    representation = get_representation(destination, representation=representation)
    if representation == "ows":
        owscheme.ewoks_to_ows(graph, destination, **save_options)
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


__deprecated_submodules__ = {
    "owsconvert": "ewoksorange.bindings.owsconvert",
    "owwidgets": "ewoksorange.bindings.owwidgets",
    "progress": "ewoksorange.bindings.progress",
    "taskwrapper": "ewoksorange.bindings.taskwrapper",
}


def __getattr__(name):
    for full_module in __deprecated_submodules__.values():
        try:
            submod = importlib.import_module(full_module)
            if hasattr(submod, name):
                warnings.warn(
                    f"Accessing '{name}' from '{__name__}' is deprecated. "
                    f"Please import from '{full_module}' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                return getattr(submod, name)
        except ImportError:
            continue

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
