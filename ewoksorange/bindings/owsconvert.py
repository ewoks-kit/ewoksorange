import json
import logging
from collections import namedtuple
from typing import IO, Iterator, List, Optional, Tuple, Type, Union

from ..orange_version import ORANGE_VERSION

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    from oasys.widgets.widget import OWWidget as OWBaseWidget
    from orangecanvas.scheme import readwrite
elif ORANGE_VERSION == ORANGE_VERSION.henri_fork:
    from Orange.widgets.widget import OWWidget as OWBaseWidget
    from Orange.canvas.scheme import readwrite
else:
    from orangewidget.widget import OWBaseWidget
    from orangecanvas.scheme import readwrite

from ewokscore import load_graph
from ewokscore.utils import qualname
from ewokscore.utils import import_qualname
from ewokscore.graph import TaskGraph
from ewokscore.inittask import task_executable_info
from ewokscore.task import Task
from ewokscore.node import get_node_label

from ..registration import get_owwidget_descriptions
from .taskwrapper import OWWIDGET_TASKS_GENERATOR
from .owsignals import signal_ewoks_to_orange_name
from .owsignals import signal_orange_to_ewoks_name
from .owwidgets import is_ewoks_widget_class
from ..ewoks_addon.orangecontrib.ewoks_defaults import default_owwidget_class

__all__ = ["ows_to_ewoks", "ewoks_to_ows"]

ReadSchemeType = readwrite._scheme

logger = logging.getLogger(__name__)


def widget_to_task(widget_qualname: str) -> Tuple[OWBaseWidget, dict, Optional[Task]]:
    try:
        widget_class = import_qualname(widget_qualname)
    except ImportError:
        widget_class = None
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
        return default_owwidget_class(import_qualname(task_qualname))
    if len(all_widgets) == 1 or not error_on_duplicates:
        return all_widgets[0]
    raise RuntimeError("More than one widget for task " + task_qualname, all_widgets)


def node_data_to_default_inputs(
    data: dict, widget_class: Type[OWBaseWidget], ewokstaskclass: Type[Task]
) -> List[dict]:
    if data is None:
        return list()
    node_properties = readwrite.loads(data.data, data.format)
    if is_ewoks_widget_class(widget_class):
        default_inputs = node_properties.get("default_inputs", dict())
    else:
        if ewokstaskclass:
            default_inputs = {
                name: value
                for name, value in node_properties.items()
                if name in ewokstaskclass.input_names()
            }
        else:
            default_inputs = node_properties
    return [{"name": name, "value": value} for name, value in default_inputs.items()]


def ows_to_ewoks(
    source: Union[str, IO],
    preserve_ows_info: bool = False,
    title_as_node_id: bool = False,
) -> TaskGraph:
    """Load an Orange Workflow Scheme from a file or stream and convert it to a `TaskGraph`."""
    ows = read_ows(source)

    description = ows.description
    try:
        ewoksinfo = json.loads(description)
        description = ewoksinfo["description"]
    except Exception:
        ewoksinfo = dict()

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
            ows_node.qualified_name
        )
        owsinfo = {
            "title": ows_node.title,
            "name": ows_node.name,
            "position": ows_node.position,
            "version": ows_node.version,
        }
        node_attrs["id"] = id_to_title.get(ows_node.id, ows_node.id)
        node_attrs["label"] = ows_node.title
        if preserve_ows_info:
            node_attrs["ows"] = owsinfo
        if widget_class is not None:
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
            "data_mapping": [{"target_input": sink_name, "source_output": source_name}],
        }
        links.append(link)

    links += ewoksinfo.get("missing_links", list())

    graph_attrs = dict()
    if ows.title:
        graph_attrs["id"] = ows.title
        graph_attrs["label"] = description

    graph = {
        "graph": graph_attrs,
        "links": links,
        "nodes": nodes,
    }

    return load_graph(graph)


def ewoks_to_ows(
    ewoksgraph: TaskGraph,
    destination: Union[str, IO],
    varinfo: Optional[dict] = None,
    error_on_duplicates: bool = True,
):
    """Write a TaskGraph as an Orange Workflow Scheme file. The ewoks node id's
    are lost because Orange uses node index numbers as id's.
    """
    if ewoksgraph.is_cyclic:
        raise RuntimeError("Orange can only execute DAGs")
    if ewoksgraph.has_conditional_links:
        raise RuntimeError("Orange cannot handle conditional links")
    owsgraph = OwsSchemeWrapper(
        ewoksgraph, varinfo, error_on_duplicates=error_on_duplicates
    )
    write_ows(owsgraph, destination)


class OwsNodeWrapper:
    """Only part of the API used by scheme_to_ows_stream"""

    _node_desc = namedtuple(
        "NodeDescription",
        ["name", "qualified_name", "version", "project_name"],
    )

    def __init__(self, node_attrs: dict):
        ows = node_attrs.get("ows", dict())
        node_id = node_attrs["id"]
        node_label = get_node_label(node_attrs, node_id=node_id)
        self.title = ows.get("title", node_label)
        self.position = ows.get("position", (0.0, 0.0))
        default_name = node_attrs["qualified_name"].split(".")[-1]
        self.description = self._node_desc(
            name=ows.get("name", default_name),
            qualified_name=node_attrs["qualified_name"],
            project_name=node_attrs["project_name"],
            version=ows.get("version", ""),
        )
        default_inputs = node_attrs.get("default_inputs", list())
        default_inputs = {item["name"]: item["value"] for item in default_inputs}
        self.properties = {
            "default_inputs": default_inputs,
            "varinfo": node_attrs.get("varinfo", dict()),
        }

    def __str__(self):
        return self.title


class OwsSchemeWrapper:
    """Only the part of the scheme API used by scheme_to_ows_stream"""

    _link = namedtuple(
        "Link",
        ["source_node", "sink_node", "source_channel", "sink_channel", "enabled"],
    )
    _link_channel = namedtuple(
        "Linkchannel",
        ["name"],
    )

    def __init__(self, graph, varinfo, error_on_duplicates=True):
        if isinstance(graph, TaskGraph):
            graph = graph.dump()
        if varinfo is None:
            varinfo = dict()

        self.title = graph["graph"].get("id", "")
        self._description = graph["graph"].get("label", "")

        self._nodes = dict()  # the keys of this dictionary never used
        self._widget_classes = dict()
        for node_attrs in graph["nodes"]:
            task_type, task_info = task_executable_info(node_attrs)
            if task_type != "class":
                raise ValueError("Orange workflows only support task type 'class'")
            widget_class, node_attrs["project_name"] = task_to_widget(
                task_info["task_identifier"], error_on_duplicates=error_on_duplicates
            )
            node_attrs["qualified_name"] = qualname(widget_class)
            node_attrs["varinfo"] = varinfo
            self._nodes[node_attrs["id"]] = OwsNodeWrapper(node_attrs)
            self._widget_classes[node_attrs["id"]] = widget_class

        self.links = list()
        self.missing_links = list()
        for link in graph["links"]:
            self._convert_link(link)

    @property
    def nodes(self):
        return list(self._nodes.values())

    @property
    def annotations(self):
        return list()

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
        source_node = self._nodes[link["source"]]
        sink_node = self._nodes[link["target"]]
        source_class = self._widget_classes[link["source"]]
        sink_class = self._widget_classes[link["target"]]
        data_mapping = link.get("data_mapping", None)
        if not data_mapping:
            logger.warning(
                "link '%s' -> '%s' cannot be created in Orange because it has not data transfer",
                source_node,
                sink_node,
            )
            self.missing_links.append(link)
            return
        for item in data_mapping:
            target_name = item["target_input"]
            source_name = item["source_output"]
            target_name = signal_ewoks_to_orange_name(sink_class, "inputs", target_name)
            source_name = signal_ewoks_to_orange_name(
                source_class, "outputs", source_name
            )
            sink_channel = self._link_channel(name=target_name)
            source_channel = self._link_channel(name=source_name)
            link = self._link(
                source_node=source_node,
                sink_node=sink_node,
                source_channel=source_channel,
                sink_channel=sink_channel,
                enabled=True,
            )
            self.links.append(link)

    def window_group_presets(self):
        return list()


def read_ows(source: Union[str, IO]) -> ReadSchemeType:
    """Read an Orange Workflow Scheme from a file or a stream."""
    return readwrite.parse_ows_stream(source)


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
    tree.write(destination, encoding="utf-8", xml_declaration=True)
