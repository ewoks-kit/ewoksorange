"""Each Orange3 Addon install entry-points for widgets and tutorials.

Widget discovery is done in `orangecanvas.registry.discovery.WidgetDiscovery`
"""

import pkgutil
import importlib
import pkg_resources
import logging
from contextlib import contextmanager

# first check if we are on the old orange3 fork
try:
    from Orange.canvas.registry.discovery import WidgetDiscovery
    from Orange.canvas.registry.base import WidgetRegistry
except ImportError:
    # from orangecanvas.registry.discovery import WidgetDiscovery
    from orangewidget.workflow.discovery import WidgetDiscovery
    from orangecanvas.registry.base import WidgetRegistry


from ewoksorange import setuptools

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
            logger.debug(f"Dynamically add entry point for '{distroname}': {ep}")


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


@contextmanager
def register_addon_package(package, distroname=None):
    """An Orange Addon package which has not been installed.

    :param package:
    :param str distroname:
    """
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
    for ep in pkg_resources.iter_entry_points(group):
        if ep.dist.project_name.lower() != "orange3":
            yield ep


def get_owwidget_descriptions():
    reg = WidgetRegistry()
    disc = WidgetDiscovery(reg)
    disc.run(iter_entry_points(setuptools.WIDGET_GROUP))
    return reg.widgets()
