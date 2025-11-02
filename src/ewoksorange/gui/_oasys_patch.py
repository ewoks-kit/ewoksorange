import importlib.metadata
from types import MethodType

from packaging.version import Version

from ..orange_version import ORANGE_VERSION
from ..pkg_meta import get_distribution


def oasys_patch():
    """OASYS1 and ewoksorange have conflicting dependencies.
    This patch ensures the oasys.widgets entry points can
    be resolved (missing dependencies causes them to fail).
    """
    if ORANGE_VERSION != ORANGE_VERSION.oasys_fork:
        return

    if Version(importlib.metadata.version("oasys-canvas-core")) >= Version("1.0.10"):
        return

    def requires(self, extras=()):
        return []

    dist = get_distribution("OASYS1", raise_error=True)
    dist.requires = MethodType(requires, dist)
    dist = get_distribution("ewoksorange", raise_error=True)
    dist.requires = MethodType(requires, dist)
