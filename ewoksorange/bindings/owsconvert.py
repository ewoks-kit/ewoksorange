from collections import namedtuple
from typing import Iterator, List, Tuple

from ..orange_version import ORANGE_VERSION

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    from oasys.widgets.widget import OWWidget as OWBaseWidget
elif ORANGE_VERSION == ORANGE_VERSION.henri_fork:
    from Orange.widgets.widget import OWWidget as OWBaseWidget
else:
    from orangewidget.widget import OWBaseWidget
from orangecanvas.scheme import readwrite

from ewokscore import load_graph
from ewokscore.utils import qualname
from ewokscore.utils import import_qualname
from ewokscore.graph import TaskGraph
from ewokscore.inittask import task_executable_info

from ..registration import get_owwidget_descriptions
from .taskwrapper import OWWIDGET_TASKS_GENERATOR
from .owsignals import signal_ewoks_to_orange_name
from .owsignals import signal_orange_to_ewoks_name
from .owwidgets import is_ewoks_widget_class
from ..ewoks_addon.orangecontrib.ewoks_defaults import default_owwidget_class

__all__ = ["ows_to_ewoks", "ewoks_to_ows"]


def widget_to_task(widget_qualname) -> Tuple[OWBaseWidget, dict]:
    try:
        widget_class = import_qualname(widget_qualname)
    except ImportError:
        widget_class = None
    if hasattr(widget_class, "ewokstaskclass"):
        # Ewoks Orange widget
        return widget_class, {
            "task_type": "class",
            "task_identifier": widget_class.ewokstaskclass.class_registry_name(),
        }
    else:
        # Native Orange widget
        return widget_class, {
            "task_type": "generated",
            "task_identifier": widget_qualname,
            "task_generator": OWWIDGET_TASKS_GENERATOR,
        }


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


def read_ows(source):
    """Read an Orange Workflow Scheme

    :param str or stream source:
    :returns NamedTuple:
    """
    if isinstance(source, str):
        with open(source, mode="rb") as stream:
            return readwrite.parse_ows_stream(stream)
    else:
        return readwrite.parse_ows_stream(source)


def write_ows(scheme, destination):
    """Write an Orange Workflow Scheme

    :param OwsSchemeWrapper scheme:
    :param str or stream destination:
    """
    if not isinstance(scheme, OwsSchemeWrapper):
        raise TypeError(scheme, type(scheme))
    if isinstance(destination, str):
        with open(destination, mode="wb") as stream:
            scheme_to_ows_stream(scheme, stream)
    else:
        scheme_to_ows_stream(scheme, destination)


def scheme_to_ows_stream(scheme, stream):
    """Write an Orange Workflow Scheme

    :param OwsSchemeWrapper scheme:
    :param str or stream destination:
    :returns NamedTuple:
    """
    if not isinstance(scheme, OwsSchemeWrapper):
        raise TypeError(scheme, type(scheme))
    tree = readwrite.scheme_to_etree(scheme, data_format="literal")
    for node in tree.getroot().find("nodes"):
        del node.attrib["scheme_node_type"]
    readwrite.indent(tree.getroot(), 0)
    tree.write(stream, encoding="utf-8", xml_declaration=True)


def node_data_to_default_inputs(data: dict, widget_class) -> List[dict]:
    if data is None:
        return list()
    node_properties = readwrite.loads(data.data, data.format)
    if is_ewoks_widget_class(widget_class):
        default_inputs = node_properties.get("default_inputs", dict())
    else:
        default_inputs = node_properties
    return [{"name": name, "value": value} for name, value in default_inputs.items()]


def ows_to_ewoks(filename, preserve_ows_info=False):
    """Load an Orange Workflow Scheme from a file and convert it
    to a `TaskGraph`.

    :param str filename:
    :returns TaskGraph:
    """
    ows = read_ows(filename)

    idmap = {ows_node.id: ows_node.name for ows_node in ows.nodes}
    if len(set(idmap.values())) != len(ows.nodes):
        idmap = {ows_node.id: ows_node.id for ows_node in ows.nodes}

    nodes = list()
    widget_classes = dict()
    for ows_node in ows.nodes:
        widget_class, node_attrs = widget_to_task(ows_node.qualified_name)
        owsinfo = {
            "title": ows_node.title,
            "name": ows_node.name,
            "position": ows_node.position,
            "version": ows_node.version,
        }
        node_attrs["id"] = idmap[ows_node.id]
        if preserve_ows_info:
            node_attrs["ows"] = owsinfo
        if widget_class is not None:
            node_attrs["default_inputs"] = node_data_to_default_inputs(
                ows_node.data, widget_class
            )
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
            "source": idmap[ows_link.source_node_id],
            "target": idmap[ows_link.sink_node_id],
            "data_mapping": [{"target_input": sink_name, "source_output": source_name}],
        }
        links.append(link)

    graph_attrs = dict()
    if ows.title:
        graph_attrs["name"] = ows.title

    graph = {
        "graph": graph_attrs,
        "links": links,
        "nodes": nodes,
    }

    return load_graph(graph)


def ewoks_to_ows(ewoksgraph, destination, varinfo=None, error_on_duplicates=True):
    """Write a TaskGraph as an Orange Workflow Scheme file.

    :param TaskGraph ewoksgraph:
    :param str or stream destination:
    :param bool error_on_duplicates:
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

    def __init__(self, adict):
        ows = adict.get("ows", dict())

        self.title = ows.get("title", adict["id"])
        self.position = ows.get("position", (0.0, 0.0))

        self.description = self._node_desc(
            name=ows.get("name", adict["id"]),
            qualified_name=adict["qualified_name"],
            project_name=adict["project_name"],
            version=ows.get("version", ""),
        )

        default_inputs = adict.get("default_inputs", list())
        default_inputs = {item["name"]: item["value"] for item in default_inputs}
        self.properties = {
            "default_inputs": default_inputs,
            "varinfo": adict.get("varinfo", dict()),
        }

    def __str__(self):
        return self.title


class OwsSchemeWrapper:
    """Only part of the API used by scheme_to_ows_stream"""

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

        self.title = graph["graph"].get("name", "")
        self.description = self.title

        self._nodes = dict()
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
        for link in graph["links"]:
            self._convert_link(link)

    @property
    def nodes(self):
        return list(self._nodes.values())

    @property
    def annotations(self):
        return list()

    def _convert_link(self, link):
        source_node = self._nodes[link["source"]]
        sink_node = self._nodes[link["target"]]
        source_class = self._widget_classes[link["source"]]
        sink_class = self._widget_classes[link["target"]]
        for item in link["data_mapping"]:
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
