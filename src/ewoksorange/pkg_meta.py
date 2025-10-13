import importlib.metadata
from typing import Optional

from packaging.version import Version

try:
    _USE_IMPORTLIB = Version(
        importlib.metadata.version("orange-canvas-core")
    ) >= Version("0.2.0")
    # orange-canvas-core>=0.2.0
    # orange-widget-base>=4.23.0
    # orange3>=3.37.0
    #
    # https://github.com/biolab/orange-canvas-core/pull/289
    # https://github.com/biolab/orange-widget-base/pull/260
    # https://github.com/biolab/orange3/pull/6655
except importlib.metadata.PackageNotFoundError as ex:
    try:
        _USE_IMPORTLIB = Version(
            importlib.metadata.version("oasys-canvas-core")
        ) >= Version("1.0.10")
        # Oasys-Canvas-Core   1.0.10
        # Oasys-Widget-Core   1.0.5
        # OASYS1              1.2.148
    except importlib.metadata.PackageNotFoundError:
        raise ex


if _USE_IMPORTLIB:
    from ewokscore.entry_points import EntryPoint  # noqa F401
    from ewokscore.entry_points import entry_points  # noqa F401

    def get_distribution(
        name: str, raise_error: bool = False
    ) -> Optional[importlib.metadata.Distribution]:
        try:
            return importlib.metadata.Distribution.from_name(name)
        except importlib.metadata.PackageNotFoundError:
            if raise_error:
                raise

    def get_distribution_name(distribution: importlib.metadata.Distribution) -> str:
        return distribution.name

else:
    import pkg_resources
    from pkg_resources import EntryPoint  # noqa F401
    from pkg_resources import iter_entry_points as entry_points  # noqa F401

    def get_distribution(
        name: str, raise_error: bool = False
    ) -> Optional[pkg_resources.Distribution]:
        try:
            return pkg_resources.get_distribution(name)
        except pkg_resources.DistributionNotFound:
            if raise_error:
                raise

    def get_distribution_name(distribution: pkg_resources.Distribution) -> str:
        return distribution.project_name
