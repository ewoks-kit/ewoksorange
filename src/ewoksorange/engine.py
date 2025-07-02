import pathlib
from typing import Any, Optional, Union, List

from ewokscore.engine_interface import Path
from ewokscore.engine_interface import TaskGraph
from ewokscore.engine_interface import RawExecInfoType
from ewokscore.engine_interface import WorkflowEngineWithSerialization

from . import bindings


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
        bindings.execute_graph(
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
        return bindings.load_graph(
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
        return bindings.save_graph(
            graph, destination, representation=representation, **serialize_options
        )

    def can_serialize_graph(
        self,
        graph: Any,
        *,
        representation: Optional[str] = None,
    ) -> bool:
        if representation == "ows":
            return True
        if isinstance(graph, str) and graph.endswith(".ows"):
            return True
        if isinstance(graph, pathlib.Path) and graph.suffix == ".ows":
            return True
        return False
