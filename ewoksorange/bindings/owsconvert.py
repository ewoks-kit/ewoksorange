from collections import namedtuple
from typing import Iterator, Tuple

from Orange.widgets.widget import OWWidget
from orangecanvas.scheme import readwrite

from ewokscore import load_graph
from ewokscore.utils import qualname
from ewokscore.utils import import_qualname
from ewokscore.graph import TaskGraph

from ..registration import get_owwidget_descriptions
from .taskwrapper import OWWIDGET_TASKS_GENERATOR
from .ewoksowsignals import get_signals


__all__ = ["ows_to_ewoks", "ewoks_to_ows"]


def widget_to_task(widget_qualname) -> Tuple[OWWidget, dict]:
    widget_class = import_qualname(widget_qualname)
    if hasattr(widget_class, "ewokstaskclass"):
        # Ewoks Orange widget
        return widget_class, {
            "class": widget_class.ewokstaskclass.class_registry_name()
        }
    else:
        # Native Orange widget
        return widget_class, {
            "task": widget_qualname,
            "task_generator": OWWIDGET_TASKS_GENERATOR,
        }


def task_to_widgets(task_qualname: str) -> Iterator[OWWidget]:
    """The `task_qualname` could be an ewoks task or an orange widget"""
    for class_desc in get_owwidget_descriptions():
        widget_class = import_qualname(class_desc.qualified_name)
        if hasattr(widget_class, "ewokstaskclass"):
            regname = widget_class.ewokstaskclass.class_registry_name()
            if regname.endswith(task_qualname):
                yield widget_class, class_desc.project_name
        elif class_desc.qualified_name == task_qualname:
            yield widget_class, class_desc.project_name


def task_to_widget(task_qualname: str, error_on_duplicates: bool = True) -> OWWidget:
    """The `task_qualname` could be an ewoks task or an orange widget"""
    all_widgets = list(task_to_widgets(task_qualname))
    if not all_widgets:
        raise RuntimeError("No OWWidget found for task " + task_qualname)
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


def find_argument_by_name(signals_class, orangename):
    for ewoksname, signal in get_signals(signals_class).items():
        if signal.name == orangename:
            return ewoksname
    raise RuntimeError(f"{orangename} is not a signal of {signals_class}")


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
    classes = dict()
    for ows_node in ows.nodes:
        data = ows_node.data
        if data is None:
            static_input = dict()
        else:
            node_properties = readwrite.loads(data.data, data.format)
            static_input = node_properties.get("static_input", dict())
        owsinfo = {
            "title": ows_node.title,
            "name": ows_node.name,
            "position": ows_node.position,
            "version": ows_node.version,
        }
        class_obj, node_attrs = widget_to_task(ows_node.qualified_name)
        node_attrs["id"] = idmap[ows_node.id]
        node_attrs["inputs"] = static_input
        if preserve_ows_info:
            node_attrs["ows"] = owsinfo
        nodes.append(node_attrs)
        classes[ows_node.id] = class_obj

    links = list()
    for ows_link in ows.links:
        outputs = classes[ows_link.source_node_id].Outputs
        source_channel = find_argument_by_name(outputs, ows_link.source_channel)
        inputs = classes[ows_link.sink_node_id].Inputs
        sink_channel = find_argument_by_name(inputs, ows_link.sink_channel)
        link = {
            "source": idmap[ows_link.source_node_id],
            "target": idmap[ows_link.sink_node_id],
            "arguments": {sink_channel: source_channel},
        }
        links.append(link)

    graph = {
        "directed": True,
        "graph": {"name": ows.title},
        "links": links,
        "multigraph": True,
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

        self.properties = {
            "static_input": adict.get("inputs", dict()),
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

        self.title = graph["graph"]["name"]
        self.description = graph["graph"]["name"]

        self._nodes = dict()
        self._classes = dict()
        for adict in graph["nodes"]:
            class_obj, adict["project_name"] = task_to_widget(
                adict["class"], error_on_duplicates=error_on_duplicates
            )
            adict["qualified_name"] = qualname(class_obj)
            adict["varinfo"] = varinfo
            self._nodes[adict["id"]] = OwsNodeWrapper(adict)
            self._classes[adict["id"]] = class_obj

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
        source_class = self._classes[link["source"]]
        sink_class = self._classes[link["target"]]
        for sink_channel, source_channel in link["arguments"].items():
            sink_channel = getattr(sink_class.Inputs, sink_channel).name
            source_channel = getattr(source_class.Outputs, source_channel).name
            sink_channel = self._link_channel(name=sink_channel)
            source_channel = self._link_channel(name=source_channel)
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
