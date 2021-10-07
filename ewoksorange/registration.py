"""Each Orange3 Addon install entry-points for widgets and tutorials.

Widget discovery is done in `orangecanvas.registry.discovery.WidgetDiscovery`
"""

import pkgutil
import importlib
from typing import List, Optional
import pkg_resources
import logging

from .orange_version import ORANGE_VERSION

if ORANGE_VERSION == ORANGE_VERSION.henri_fork:
    from Orange.canvas.registry.discovery import WidgetDiscovery
    from Orange.canvas.registry.base import WidgetRegistry
    from Orange.canvas.registry.description import WidgetDescription
    from Orange.canvas.registry import global_registry

    from Orange.canvas.registry.description import CategoryDescription

    category_from_package_globals = CategoryDescription.from_package
else:
    # from orangecanvas.registry.discovery import WidgetDiscovery
    from orangewidget.workflow.discovery import WidgetDiscovery
    from orangecanvas.registry.base import WidgetRegistry
    from orangecanvas.registry import WidgetDescription
    from orangecanvas.registry import global_registry
    from orangecanvas.registry.utils import category_from_package_globals


from ewoksorange import setuptools
from .canvas.utils import get_orange_canvas

logger = logging.getLogger(__name__)


def get_distribution(distroname):
    try:
        return pkg_resources.get_distribution(distroname)
    except Exception:
        return None


def add_entry_points(distribution, entry_points):
    """Add entry points to a package distribution

    :param dict entry_points: mapping of "groupname" to a list of entry points
                              ["ep1 = destination1", "ep1 = destination2", ...]
    """
    if isinstance(distribution, str):
        distroname = distribution
        dist = get_distribution(distroname)
        if dist is None:
            logger.error(
                "Distribution '%s' not found. Existing distributions:\n %s",
                distroname,
                list(pkg_resources.working_set.by_key.keys()),
            )
            raise pkg_resources.DistributionNotFound(distroname, [repr("ewoksorange")])
    else:
        dist = distribution
        distroname = dist.project_name

    entry_map = dist.get_entry_map()
    for group, lst in entry_points.items():
        group_map = entry_map.setdefault(group, dict())
        for entry_point in lst:
            ep = pkg_resources.EntryPoint.parse(entry_point, dist=dist)
            if ep.name in group_map:
                raise ValueError(
                    f"Entry point {repr(ep.name)} already exists in group {repr(group)} of distribution {repr(distroname)}"
                )
            group_map[ep.name] = ep
            logger.debug("Dynamically add entry point for '%s': %s", distroname, ep)


def create_fake_distribution(distroname, location):
    distroname = pkg_resources.safe_name(distroname)
    dist = get_distribution(distroname)
    if dist is not None:
        raise RuntimeError(
            f"A distribution with the name {repr(distroname)} already exists"
        )
    if isinstance(location, list):
        location = location[0]
    from ewoksorange import __version__

    dist = pkg_resources.Distribution(
        location=location, project_name=distroname, version=__version__
    )
    pkg_resources.working_set.add(dist)
    return dist


def get_subpackages(package):
    for pkginfo in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        if pkginfo.ispkg:
            yield importlib.import_module(pkginfo.name)


def register_addon_package(package, distroname: Optional[str] = None):
    """An Orange Addon package which has not been installed."""
    entry_points = dict()
    packages = list(get_subpackages(package))
    if not distroname:
        distroname = package.__name__.split(".")[-1]
    setuptools.update_entry_points(packages, entry_points, distroname)
    dist = create_fake_distribution(distroname, package.__path__)
    add_entry_points(dist, entry_points)


def widget_discovery(discovery, distroname, subpackages):
    dist = pkg_resources.get_distribution(distroname)
    for pkg in subpackages:
        discovery.process_category_package(pkg, distribution=dist)


def iter_entry_points(group):
    """Do not include native orange entry points"""
    for ep in pkg_resources.iter_entry_points(group):
        if ep.dist.project_name.lower() != "orange3":
            yield ep


def global_registry_objects() -> List[WidgetRegistry]:
    registry_objects = list()
    scene = None
    canvas = get_orange_canvas()
    if canvas is not None:
        scene = canvas.current_document()
        reg = canvas.widget_registry
        if reg is not None:
            registry_objects.append(reg)
    if ORANGE_VERSION != ORANGE_VERSION.henri_fork and scene is not None:
        reg = scene.registry()
        if reg is not None:
            registry_objects.append(reg)
    if not registry_objects:
        reg = global_registry()
        if reg is not None:
            registry_objects.append(reg)
    return registry_objects


def global_discovery_objects() -> List[WidgetDiscovery]:
    return [WidgetDiscovery(reg) for reg in global_registry_objects()]


def local_discovery_object() -> WidgetDiscovery:
    return WidgetDiscovery(WidgetRegistry())


def get_owwidget_descriptions():
    """Do not include native orange widgets"""
    disc = local_discovery_object()
    disc.run(iter_entry_points(setuptools.WIDGET_GROUP))
    return disc.registry.widgets()


def get_owwidget_description(
    widget_class, package_name: str, category_name: str, project_name: str
):
    kwargs = widget_class.get_widget_description()

    if ORANGE_VERSION == ORANGE_VERSION.henri_fork:
        for key in ["inputs", "outputs"]:
            for s in kwargs[key]:
                s.type = "%s.%s" % (s.type.__module__, s.type.__name__)

    description = WidgetDescription(**kwargs)
    description.package = setuptools.orangecontrib_qualname(package_name)
    description.category = widget_class.category or category_name
    description.project_name = project_name
    return description


def get_owcategory_description(
    package_name: str, category_name: str, project_name: str
):
    description = category_from_package_globals(package_name)
    description.name = category_name
    description.project_name = project_name
    return description


def register_owcategory(
    package_name: str,
    category_name: str,
    project_name: str,
    discovery_object: Optional[WidgetDiscovery] = None,
):
    description = get_owcategory_description(package_name, category_name, project_name)
    if discovery_object is None:
        for discovery_object in global_discovery_objects():
            discovery_object.handle_category(description)
    else:
        discovery_object.handle_category(description)


def register_owwidget(
    widget_class,
    package_name: str,
    category_name: str,
    project_name: str,
    discovery_object: Optional[WidgetDiscovery] = None,
):
    register_owcategory(
        package_name, category_name, project_name, discovery_object=discovery_object
    )
    description = get_owwidget_description(
        widget_class, package_name, category_name, project_name
    )

    logger.debug("Register widget: %s", description.qualified_name)
    if discovery_object is None:
        for discovery_object in global_discovery_objects():
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
