import logging
from typing import Optional

try:
    # pip install "orange-canvas-core>=0.2.0" "orange-widget-base>=4.23.0"
    from orangecanvas.utils.pkgmeta import entry_points as _entry_points
    from orangecanvas.utils.pkgmeta import Distribution as _Distribution
    from orangecanvas.utils.pkgmeta import PackageNotFoundError as _PackageNotFoundError

    def iter_entry_points(group: str):
        try:
            return _entry_points(group=group)
        except Exception:
            return _entry_points().get(group, [])

    def get_distribution(
        name: str, raise_error: bool = False
    ) -> Optional[_Distribution]:
        try:
            return _Distribution.from_name(name)
        except _PackageNotFoundError:
            if raise_error:
                raise

    def get_distribution_name(distribution: _Distribution) -> str:
        return distribution.name

except ImportError:
    # pip install "orange-canvas-core<0.2.0" "orange-widget-base<4.23.0"
    from pkg_resources import Distribution as _Distribution
    from pkg_resources import DistributionNotFound as _DistributionNotFound
    from pkg_resources import iter_entry_points  # noqa F401
    from pkg_resources import get_distribution as _get_distribution

    def get_distribution(
        name: str, raise_error: bool = False
    ) -> Optional[_Distribution]:
        try:
            return _get_distribution(name)
        except _DistributionNotFound:
            if raise_error:
                raise

    def get_distribution_name(distribution: _Distribution) -> str:
        return distribution.project_name


logger = logging.getLogger(__name__)
