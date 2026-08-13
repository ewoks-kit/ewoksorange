import contextlib
import importlib
import sys
import warnings
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Generator
from typing import List
from typing import Optional
from typing import Union

import ewokscore
import networkx
from ewokscore.graph import TaskGraph
from ewokscore.graph import graph_io
from ewokscore.graph.serialize import GraphRepresentation
from ewokscore.node import get_node_label

from ..gui.canvas.handler import OrangeCanvasHandler
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
    no_gui: bool = False,
    orange_canvas_handler: Optional[OrangeCanvasHandler] = None,
    timeout: Optional[float] = None,
) -> Optional[Dict]:
    """`orange_canvas_handler` (only relevant when `no_gui=True`) reuses that
    `OrangeCanvasHandler` instead of creating and closing a fresh one for this
    call.
    """
    if outputs and not no_gui:
        raise ValueError(
            "The Orange3 binding cannot return any results unless `no_gui=True`"
        )
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
        if no_gui:
            with _orange_canvas_handler(orange_canvas_handler) as handler:
                exception: Optional[BaseException] = None
                try:
                    handler.load_ows(ows_filename)
                    handler.start_workflow()
                    handler.wait_widgets(timeout=timeout)
                    if outputs is None:
                        return None
                    taskgraph = load_graph(
                        graph, inputs=inputs, **(load_options or dict())
                    )
                    return _get_output_values(
                        handler, taskgraph.graph, outputs, merge_outputs=merge_outputs
                    )
                except BaseException as e:
                    exception = e
                    raise
                finally:
                    # Needed for the ewoks events
                    try:
                        handler.scheme.ewoks_finalize(exception=exception)
                    except AttributeError:
                        pass
        argv = [sys.argv[0], ows_filename]
        launchcanvas(argv=argv)


@contextlib.contextmanager
def _orange_canvas_handler(
    handler: Optional[OrangeCanvasHandler] = None,
) -> Generator[OrangeCanvasHandler, None, None]:
    """Yield `handler` as-is, or a fresh `OrangeCanvasHandler` (created and closed
    here) when not provided."""
    if handler is not None:
        yield handler
        return
    with OrangeCanvasHandler() as handler:
        yield handler


def _get_output_values(
    handler: OrangeCanvasHandler,
    graph,
    outputs: List[dict],
    merge_outputs: Optional[bool] = True,
) -> Dict:
    parsed_outputs = graph_io.parse_outputs(graph, outputs)
    output_values: Dict = dict()
    for node_id in networkx.topological_sort(graph):
        label = get_node_label(node_id, graph.nodes[node_id])
        widgets = list(handler.widgets_from_name(label))
        if not widgets:
            raise RuntimeError(f"No Orange widget found for node {node_id!r}")
        task_output_values = widgets[0].get_task_output_values()
        graph_io.add_output_values(
            output_values,
            node_id,
            task_output_values,
            parsed_outputs,
            merge_outputs=merge_outputs,
        )
    return output_values


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
