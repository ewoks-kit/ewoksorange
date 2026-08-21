"""Each Orange3 add-on installs entry-points for widgets and tutorials.

Widget and example discovery is done from these entry-points.
"""

import logging
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from orangecanvas.registry import WidgetDescription
from orangecanvas.registry import global_registry
from orangecanvas.registry.base import WidgetRegistry
from orangecanvas.registry.utils import category_from_package_globals

# Not `orangecanvas.registry.WidgetDiscovery`: that one describes widgets from
# module globals, while Ewoks widgets are only described by their class.
from orangewidget.workflow.discovery import WidgetDiscovery

from ... import pkg_meta
from ...orange_version import ORANGE_VERSION
from ..canvas.config import WIDGETS_ENTRY  # "orange.widgets" or "oasys2.widgets"
from ..canvas.utils import get_orange_canvas

if ORANGE_VERSION == ORANGE_VERSION.latest_oasys:
    NATIVE_WIDGETS_PROJECT = "oasys2"
else:
    NATIVE_WIDGETS_PROJECT = "orange3"

NAMESPACE_PACKAGE = "orangecontrib"

logger = logging.getLogger(__name__)

# Widget qualifier to project name mapping for dynamically registered widgets.
_DYNAMIC_WIDGET_PROJECT_NAMES: Dict[str, str] = {}


def get_dynamic_widget_project_name(qualified_name: str) -> Optional[str]:
    """The `project_name` a widget was given via `register_owwidget`, if any."""
    return _DYNAMIC_WIDGET_PROJECT_NAMES.get(qualified_name)


def widget_discovery(discovery, distroname, subpackages):
    """To be used by add-on which define widgets in categories"""
    dist = pkg_meta.get_distribution(distroname)
    for pkg in subpackages:
        discovery.process_category_package(pkg, distribution=dist)


def register_owwidget(
    widget_class,
    package_name: str,
    category_name: str,
    project_name: str,
    discovery_object: Optional[WidgetDiscovery] = None,
):
    """Register widgets at runtime"""
    _register_owcategory(
        package_name, category_name, project_name, discovery_object=discovery_object
    )
    description = _get_owwidget_description(
        widget_class, package_name, category_name, project_name
    )
    _DYNAMIC_WIDGET_PROJECT_NAMES[description.qualified_name] = project_name

    logger.debug("Register widget: %s", description.qualified_name)
    if discovery_object is None:
        for discovery_object in _global_widget_discovery_objects():
            if (
                discovery_object.registry is not None
                and discovery_object.registry.has_widget(description.qualified_name)
            ):
                continue
            discovery_object.handle_widget(description)
    else:
        if (
            discovery_object.registry is not None
            and discovery_object.registry.has_widget(description.qualified_name)
        ):
            return
        discovery_object.handle_widget(description)


def get_owwidget_descriptions():
    """Do not include native orange widgets"""
    discovery = _temporary_widget_discovery_object()
    discovery.run(_entry_points(WIDGETS_ENTRY))
    return discovery.registry.widgets()


def _entry_points(group: str) -> Tuple[pkg_meta.EntryPoint]:
    """Do not include native orange entry points"""
    eps = list()
    for ep in pkg_meta.entry_points(group):
        if pkg_meta.get_distribution_name(ep.dist).lower() != NATIVE_WIDGETS_PROJECT:
            eps.append(ep)
    return tuple(eps)


def _global_widget_discovery_objects() -> List[WidgetDiscovery]:
    return [WidgetDiscovery(reg) for reg in _global_registry_objects()]


def _temporary_widget_discovery_object() -> WidgetDiscovery:
    return WidgetDiscovery(WidgetRegistry())


def _global_registry_objects() -> List[WidgetRegistry]:
    registry_objects = list()
    scene = None
    canvas = get_orange_canvas()
    if canvas is not None:
        scene = canvas.current_document()
        reg = canvas.widget_registry
        if reg is not None:
            registry_objects.append(reg)
    if scene is not None:
        reg = scene.registry()
        if reg is not None:
            registry_objects.append(reg)
    if not registry_objects:
        reg = global_registry()
        if reg is not None:
            registry_objects.append(reg)
    return registry_objects


def _get_owwidget_description(
    widget_class, package_name: str, category_name: str, project_name: str
):
    kwargs = widget_class.get_widget_description()
    description = WidgetDescription(**kwargs)
    description.package = _orangecontrib_qualname(package_name)
    description.category = widget_class.category or category_name
    description.project_name = project_name
    return description


def _get_owcategory_description(
    package_name: str, category_name: str, project_name: str
):
    description = category_from_package_globals(package_name)
    description.name = category_name
    description.project_name = project_name
    return description


def _register_owcategory(
    package_name: str,
    category_name: str,
    project_name: str,
    discovery_object: Optional[WidgetDiscovery] = None,
):
    description = _get_owcategory_description(package_name, category_name, project_name)
    if discovery_object is None:
        for discovery_object in _global_widget_discovery_objects():
            discovery_object.handle_category(description)
    else:
        discovery_object.handle_category(description)


def _orangecontrib_qualname(qualname):
    if f".{NAMESPACE_PACKAGE}." in qualname:
        return (
            f"{NAMESPACE_PACKAGE}." + qualname.partition(f".{NAMESPACE_PACKAGE}.")[-1]
        )
    return qualname
