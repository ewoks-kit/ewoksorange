import json
import logging
import os
from collections import namedtuple
from pathlib import Path
from typing import IO
from typing import Iterator
from typing import List
from typing import NamedTuple
from typing import Optional
from typing import Tuple
from typing import Type
from typing import Union
from uuid import uuid4

from ewokscore import load_graph
from ewokscore.graph import TaskGraph
from ewokscore.graph.serialize import GraphRepresentation
from ewokscore.inittask import task_executable_info
from ewokscore.node import get_node_label
from ewokscore.task import Task
from ewoksutils.import_utils import import_qualname
from ewoksutils.import_utils import qualname
from orangecanvas.scheme import annotations
from orangecanvas.scheme import readwrite

from ...orange_version import ORANGE_VERSION
from ..orange_utils._signals import signal_ewoks_to_orange_name
from ..orange_utils._signals import signal_orange_to_ewoks_name
from ..orange_utils.orange_imports import OWBaseWidget
from ..owwidgets.registration import get_owwidget_descriptions
from ..owwidgets.types import is_ewoks_widget_class
from ..utils import invalid_data
from .task_wrappers import OWWIDGET_TASKS_GENERATOR

ReadSchemeType = readwrite._scheme
_original_parse_ows_stream = readwrite.parse_ows_stream
logger = logging.getLogger(__name__)


def widget_to_task(
    widget_qualname: str, task_qualname: str
) -> Tuple[Optional[OWBaseWidget], dict, Optional[Task]]:
    try:
        widget_class = import_qualname(widget_qualname)
    except ImportError:
        if task_qualname:
            try:
                widget_class, _ = task_to_widget(task_qualname)
            except ImportError:
                widget_class = None

    if not widget_class:
        logger.warning("Cannot import Orange widget %r", widget_qualname)

    if hasattr(widget_class, "ewokstaskclass"):
        # Ewoks Orange widget
        node_attrs = {
            "task_type": "class",
            "task_identifier": widget_class.ewokstaskclass.class_registry_name(),
        }
        ewokstaskclass = widget_class.ewokstaskclass
    else:
        # Native Orange widget
        node_attrs = {
            "task_type": "generated",
            "task_identifier": widget_qualname,
            "task_generator": OWWIDGET_TASKS_GENERATOR,
        }
        ewokstaskclass = None
    return widget_class, node_attrs, ewokstaskclass


def task_to_widgets(task_qualname: str) -> Iterator[Tuple[OWBaseWidget, str]]:
    """The `task_qualname` could be an ewoks task or an orange widget"""
    for class_desc in get_owwidget_descriptions():
        widget_class = import_qualname(class_desc.qualified_name)
        if hasattr(widget_class, "ewokstaskclass"):
            regname = widget_class.ewokstaskclass.class_registry_name()
            if regname.endswith(task_qualname):
                yield widget_class, class_desc.project_name
        elif class_desc.qualified_name == task_qualname:
            yield widget_class, class_desc.project_name


def task_to_widget(
    task_qualname: str, error_on_duplicates: bool = True
) -> Tuple[OWBaseWidget, str]:
    """The `task_qualname` could be an ewoks task or an orange widget"""
    all_widgets = list(task_to_widgets(task_qualname))
    if not all_widgets:
        from orangecontrib.ewoksnowidget import default_owwidget_class

        return default_owwidget_class(import_qualname(task_qualname))
    if len(all_widgets) == 1 or not error_on_duplicates:
        return all_widgets[0]
    raise RuntimeError("More than one widget for task " + task_qualname, all_widgets)


def node_data_to_default_inputs(
    data, widget_class: Type[OWBaseWidget], ewokstaskclass: Optional[Type[Task]]
) -> List[dict]:
    if data is None:
        return list()
    node_properties = readwrite.loads(data.data, data.format)
    if is_ewoks_widget_class(widget_class):
        default_inputs = node_properties.get("_ewoks_default_inputs", dict())
    elif "_ewoks_default_inputs" in node_properties:
        default_inputs = node_properties["_ewoks_default_inputs"]
    else:
        if ewokstaskclass:
            default_inputs = {
                name: value
                for name, value in node_properties.items()
                if name in ewokstaskclass.input_names()
            }
        else:
            default_inputs = node_properties
    return [
        {"name": name, "value": value}
        for name, value in default_inputs.items()
        if not invalid_data.is_invalid_data(value)
    ]


def ows_to_ewoks(
    source: Union[str, IO],
    preserve_ows_info: Optional[bool] = True,
    title_as_node_id: Optional[bool] = False,
    inputs: Optional[List[dict]] = None,
    root_dir: Optional[Union[str, Path]] = None,
    root_module: Optional[str] = None,
) -> TaskGraph:
    """Load an Orange Workflow Scheme from a file or stream and convert it to a `TaskGraph`."""
    ows = read_ows(source)

    description = ows.description
    try:
        ewoksinfo = json.loads(description)
        description = ewoksinfo["description"]
    except Exception:
        ewoksinfo = dict()
    if not description and isinstance(source, str):
        description = (
            "Ewoks workflow '%s'" % os.path.splitext(os.path.basename(source))[0]
        )
    if not description:
        description = "Ewoks workflow"

    title = ows.title
    if not title and isinstance(source, str):
        title = os.path.splitext(os.path.basename(source))[0]
    if not title:
        title = str(uuid4())

    nodes = list()
    widget_classes = dict()
    if title_as_node_id:
        id_to_title = {ows_node.id: ows_node.title for ows_node in ows.nodes}
        if len(set(id_to_title.values())) != len(id_to_title):
            id_to_title = dict()
    else:
        id_to_title = dict()

    for ows_node in ows.nodes:
        widget_class, node_attrs, ewokstaskclass = widget_to_task(
            ows_node.qualified_name, ows_node.name
        )
        owsinfo = {
            "title": ows_node.title,
            "name": ows_node.name,
            "position": str(ows_node.position),
            "version": ows_node.version,  # widget version
        }
        node_attrs["id"] = id_to_title.get(ows_node.id, ows_node.id)
        node_attrs["label"] = ows_node.title
        if preserve_ows_info:
            node_attrs["ows"] = owsinfo
        default_inputs = node_data_to_default_inputs(
            ows_node.data, widget_class, ewokstaskclass
        )
        if default_inputs:
            node_attrs["default_inputs"] = default_inputs
        widget_classes[ows_node.id] = widget_class
        nodes.append(node_attrs)

    links = list()
    for ows_link in ows.links:
        widget_class = widget_classes[ows_link.source_node_id]
        if widget_class is None:
            source_name = ows_link.source_channel
        else:
            source_name = signal_orange_to_ewoks_name(
                widget_class, "outputs", ows_link.source_channel
            )

        widget_class = widget_classes[ows_link.sink_node_id]
        if widget_class is None:
            sink_name = ows_link.sink_channel
        else:
            sink_name = signal_orange_to_ewoks_name(
                widget_class, "inputs", ows_link.sink_channel
            )

        link = {
            "source": id_to_title.get(ows_link.source_node_id, ows_link.source_node_id),
            "target": id_to_title.get(ows_link.sink_node_id, ows_link.sink_node_id),
            "data_mapping": [{"source_output": source_name, "target_input": sink_name}],
        }
        links.append(link)

    links += ewoksinfo.get("missing_links", list())

    graph_attrs = dict()
    graph_attrs["id"] = title
    graph_attrs["label"] = description
    if ows.annotations:
        graph_attrs["ows"] = {
            "annotations": [
                _serialize_annotation(annotation) for annotation in ows.annotations
            ]
        }

    graph = {
        "graph": graph_attrs,
        "links": links,
        "nodes": nodes,
    }

    return load_graph(graph, inputs=inputs, root_dir=root_dir, root_module=root_module)


def graph_is_supported(graph: TaskGraph) -> bool:
    all_explicit_datamapping = all(
        link_attrs.get("data_mapping") for link_attrs in graph.graph.edges.values()
    )
    return (
        not graph.is_cyclic
        and not graph.has_conditional_links
        and all_explicit_datamapping
    )


def ewoks_to_ows(
    graph,
    destination: Union[str, IO],
    varinfo: Optional[dict] = None,
    execinfo: Optional[dict] = None,
    task_options: Optional[dict] = None,
    error_on_duplicates: bool = True,
    inputs: Optional[List[dict]] = None,
    representation: Optional[Union[GraphRepresentation, str]] = None,
    root_dir: Optional[Union[str, Path]] = None,
    root_module: Optional[str] = None,
):
    """Save an ewoks graph as an Orange Workflow Scheme file. The ewoks node id's
    are lost because Orange uses node index numbers as id's.
    """
    ewoksgraph = load_graph(
        graph,
        inputs=inputs,
        representation=representation,
        root_dir=root_dir,
        root_module=root_module,
    )
    if ewoksgraph.is_cyclic:
        raise RuntimeError("Orange can only handle DAGs")
    if ewoksgraph.has_conditional_links:
        raise RuntimeError("Orange cannot handle conditional links")
    if not all(
        link_attrs.get("data_mapping") for link_attrs in ewoksgraph.graph.edges.values()
    ):
        raise RuntimeError("Orange cannot handle links without explicit data mapping")
    owsgraph = OwsSchemeWrapper(
        ewoksgraph,
        varinfo=varinfo,
        execinfo=execinfo,
        task_options=task_options,
        error_on_duplicates=error_on_duplicates,
    )
    write_ows(owsgraph, destination)


class OwsNodeWrapper:
    """
    Only part of the API used by scheme_to_ows_stream.
    Mimics the orange 'SchemeNode' API
    """

    _node_desc = namedtuple(
        "NodeDescription",
        ["name", "qualified_name", "version", "project_name"],
    )

    def __init__(self, orangeid: int, node_attrs: dict):
        self.id = str(orangeid)
        ows = node_attrs.get("ows", dict())
        node_id = node_attrs["id"]
        node_label = get_node_label(node_id, node_attrs)
        self.title = ows.get("title", node_label)
        self.position = ows.get("position", (0.0, 0.0))
        default_name = node_attrs["qualified_name"].split(".")[-1]
        self.description = self._node_desc(
            name=node_attrs.get("name", ows.get("name", default_name)),
            qualified_name=node_attrs["qualified_name"],
            project_name=node_attrs["project_name"],
            version=ows.get("version", ""),  # widget version
        )
        default_inputs = node_attrs.get("default_inputs", list())
        default_inputs = {item["name"]: item["value"] for item in default_inputs}
        # Note: OWEwoksBaseWidget must have these settings in the Oasys fork
        #       otherwise `WidgetsScheme.sync_node_properties` will remove the
        #       unknown properties
        self.properties = {
            "_ewoks_default_inputs": default_inputs,
            "_ewoks_varinfo": node_attrs.get("varinfo", dict()),
            "_ewoks_execinfo": node_attrs.get("execinfo", dict()),
            "_ewoks_task_options": node_attrs.get("task_options", dict()),
        }

    def __str__(self):
        return self.title


class OwsSchemeWrapper:
    """
    Only the part of the scheme API used by scheme_to_ows_stream.
    """

    _link = namedtuple(
        "Link",
        ["source_node", "sink_node", "source_channel", "sink_channel", "enabled"],
    )
    _link_channel = namedtuple(
        "Linkchannel",
        ["name", "id"],
    )

    def __init__(
        self,
        graph,
        varinfo: Optional[dict] = None,
        execinfo: Optional[dict] = None,
        task_options: Optional[dict] = None,
        error_on_duplicates: bool = True,
    ):
        if isinstance(graph, TaskGraph):
            graph = graph.dump()

        self.title = graph["graph"].get("id", "")
        self._description = graph["graph"].get("label", "")

        ows = graph["graph"].get("ows", dict())
        self._annotations = [
            _deserialize_annotation(annotation)
            for annotation in ows.get("annotations", list())
        ]

        self._nodes = dict()  # the keys of this dictionary never used
        self._widget_classes = dict()
        for orangeid, node_attrs in enumerate(graph["nodes"]):
            task_type, task_info = task_executable_info(node_attrs["id"], node_attrs)
            if task_type == "class":
                # ewoksorange widget
                widget_class, node_attrs["project_name"] = task_to_widget(
                    task_info["task_identifier"],
                    error_on_duplicates=error_on_duplicates,
                )
                node_attrs["name"] = widget_class.name
                # Ewoks Task qualified name in case of `DefaultOwWidget`
                node_attrs["qualified_name"] = qualname(widget_class)
                if varinfo:
                    node_attrs["varinfo"] = varinfo
                if execinfo:
                    node_attrs["execinfo"] = execinfo
                if task_options:
                    node_attrs["task_options"] = task_options
                self._nodes[node_attrs["id"]] = OwsNodeWrapper(orangeid, node_attrs)
                self._widget_classes[node_attrs["id"]] = widget_class
            elif task_type == "generated":
                # native widgets use-case
                widget_metaclass = import_qualname(node_attrs["task_identifier"])
                if issubclass(widget_metaclass, OWBaseWidget):
                    instance = widget_metaclass()
                    widget_class = instance.__class__
                    node_attrs["qualified_name"] = qualname(widget_class)
                    node_attrs["project_name"] = widget_class.category

                    self._nodes[node_attrs["id"]] = OwsNodeWrapper(
                        orangeid, node_attrs=node_attrs
                    )
                    self._widget_classes[node_attrs["id"]] = widget_class
                else:
                    raise ValueError(
                        "'generated' task other than native orange widget are not supported"
                    )
            else:
                raise ValueError(
                    f"Orange workflows only support task of types 'class' or 'generated'. Got {task_type!r}"
                )

        self.links = list()
        self.missing_links = list()
        for link in graph["links"]:
            self._convert_link(link)

    @property
    def nodes(self):
        return list(self._nodes.values())

    @property
    def annotations(self):
        return self._annotations

    @property
    def description(self):
        if self.missing_links:
            description = {
                "description": self._description,
                "missing_links": self.missing_links,
            }
            return json.dumps(description)
        else:
            return self._description

    def _convert_link(self, link):
        """In Orange, a link must transfer data"""
        try:
            source_node = self._nodes[link["source"]]
            sink_node = self._nodes[link["target"]]
            source_class = self._widget_classes[link["source"]]
            sink_class = self._widget_classes[link["target"]]
            data_mapping = link.get("data_mapping", None)
            if not data_mapping:
                logger.warning(
                    "link '%s' -> '%s' cannot be created in Orange because it has no data transfer",
                    source_node,
                    sink_node,
                )
                self.missing_links.append(link)
                return
            for item in data_mapping:
                target_name = item["target_input"]
                source_name = item["source_output"]
                target_name = signal_ewoks_to_orange_name(
                    sink_class, "inputs", target_name
                )
                source_name = signal_ewoks_to_orange_name(
                    source_class, "outputs", source_name
                )
                sink_channel = self._link_channel(name=target_name, id=sink_node.id)
                source_channel = self._link_channel(name=source_name, id=source_node.id)
                link2 = self._link(
                    source_node=source_node,
                    sink_node=sink_node,
                    source_channel=source_channel,
                    sink_channel=sink_channel,
                    enabled=True,
                )
                self.links.append(link2)
        except Exception as e:
            raise RuntimeError(
                f"Failed to create link '{link['source']}' -> '{link['target']}'"
            ) from e

    def window_group_presets(self):
        return list()


def read_ows(source: Union[str, IO]) -> ReadSchemeType:
    """Read an Orange Workflow Scheme from a file or a stream."""
    return _original_parse_ows_stream(source)


def write_ows(scheme: OwsSchemeWrapper, destination: Union[str, IO]):
    """Write an Orange Workflow Scheme. The ewoks node id's
    are lost because Orange uses node index numbers as id's.
    """
    if not isinstance(scheme, OwsSchemeWrapper):
        raise TypeError(scheme, type(scheme))
    tree = readwrite.scheme_to_etree(scheme, data_format="literal")
    for node in tree.getroot().find("nodes"):
        del node.attrib["scheme_node_type"]
    readwrite.indent(tree.getroot(), 0)
    if isinstance(destination, str) and os.path.dirname(destination):
        os.makedirs(os.path.dirname(destination), exist_ok=True)
    tree.write(destination, encoding="utf-8", xml_declaration=True)


def _serialize_annotation(annotation: readwrite._annotation) -> dict:
    data = _serialize_namedtuple(annotation)
    data["params"] = _serialize_namedtuple(data["params"])
    return data


def _serialize_namedtuple(ntuple: NamedTuple):
    return dict(zip(ntuple._fields, ntuple))


def _deserialize_annotation(annotation: dict) -> annotations.BaseSchemeAnnotation:
    params = dict(annotation["params"])
    if annotation["type"] == "text":
        params["rect"] = tuple(params.pop("geometry"))
        if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
            params.pop("content_type", None)
        return annotations.SchemeTextAnnotation(**params)
    if annotation["type"] == "arrow":
        start, end = params.pop("geometry")
        start = tuple(start)
        end = tuple(end)
        return annotations.SchemeArrowAnnotation(start, end, **params)
    raise ValueError("cannot deserialize annotation params")


def _patched_parse_ows_stream(*args, **kwargs) -> ReadSchemeType:
    """Add missing widgets to the `ewoksnowidget` Orange3 add-on when
    parsing `.ows` streams.
    """
    scheme = _original_parse_ows_stream(*args, **kwargs)
    for node in scheme.nodes:
        if (
            node.qualified_name.startswith("orangecontrib.ewoksnowidget.widgets.")
            and node.name
        ):
            try:
                _ = task_to_widget(node.name)
            except ImportError:
                logger.error("Ewoks task cannot be imported: %r", node.name)
    return scheme


def patch_parse_ows_stream():
    readwrite.parse_ows_stream = _patched_parse_ows_stream
