import pathlib
from typing import Any
from typing import List
from typing import Optional
from typing import Union

from ewokscore.engine_interface import Path
from ewokscore.engine_interface import RawExecInfoType
from ewokscore.engine_interface import TaskGraph
from ewokscore.engine_interface import WorkflowEngineWithSerialization

# Note: lazy import of bindings because it relies on Qt and
# we do not want to import Qt when not needed because the Qt binding
# is an optional dependency.


class OrangeWorkflowEngine(WorkflowEngineWithSerialization):

    def execute_graph(
        self,
        graph: Any,
        *,
        inputs: Optional[List[dict]] = None,
        load_options: Optional[dict] = None,
        varinfo: Optional[dict] = None,
        execinfo: RawExecInfoType = None,
        task_options: Optional[dict] = None,
        outputs: Optional[List[dict]] = None,
        merge_outputs: Optional[bool] = True,
        # Engine specific:
        error_on_duplicates: bool = True,
        tmpdir: Optional[str] = None,
    ) -> None:
        from .bindings import execute_graph

        execute_graph(
            graph,
            inputs=inputs,
            load_options=load_options,
            varinfo=varinfo,
            execinfo=execinfo,
            task_options=task_options,
            outputs=outputs,
            merge_outputs=merge_outputs,
            error_on_duplicates=error_on_duplicates,
            tmpdir=tmpdir,
        )

    def deserialize_graph(
        self,
        graph: Any,
        *,
        inputs: Optional[List[dict]] = None,
        representation: Optional[str] = None,
        root_dir: Optional[Union[str, Path]] = None,
        root_module: Optional[str] = None,
        # Serializer specific:
        preserve_ows_info: Optional[bool] = True,
        title_as_node_id: Optional[bool] = False,
    ) -> TaskGraph:
        from .bindings import load_graph

        return load_graph(
            graph,
            inputs=inputs,
            representation=representation,
            root_dir=root_dir,
            root_module=root_module,
            preserve_ows_info=preserve_ows_info,
            title_as_node_id=title_as_node_id,
        )

    def serialize_graph(
        self,
        graph: TaskGraph,
        destination,
        *,
        representation: Optional[str] = None,
        # Serializer specific:
        **serialize_options,
    ) -> Union[str, dict]:
        from .bindings import save_graph

        return save_graph(
            graph, destination, representation=representation, **serialize_options
        )

    def get_graph_representation(self, graph: Any) -> Optional[str]:
        if isinstance(graph, str) and graph.endswith(".ows"):
            return "ows"
        if isinstance(graph, pathlib.Path) and graph.suffix == ".ows":
            return "ows"
