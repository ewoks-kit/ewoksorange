from typing import List

from .pkg_meta import get_distribution


def widget_discovery(discovery, distroname: str, modules: List[str]):
    dist = get_distribution(distroname)
    for widget_category_module in modules:
        discovery.process_category_package(widget_category_module, distribution=dist)
