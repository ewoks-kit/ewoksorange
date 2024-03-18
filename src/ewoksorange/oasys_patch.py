from types import MethodType
from .pkg_meta import get_distribution
from .orange_version import ORANGE_VERSION


def oasys_patch():
    """OASYS1 and ewoksorange have conflicting dependencies.
    This patch ensures the oasys.widgets entry points can
    be resolved (missing dependencies causes them to fail).
    """
    if ORANGE_VERSION != ORANGE_VERSION.oasys_fork:
        return

    def requires(self, extras=()):
        return []

    dist = get_distribution("OASYS1", raise_error=True)
    dist.requires = MethodType(requires, dist)
    dist = get_distribution("ewoksorange", raise_error=True)
    dist.requires = MethodType(requires, dist)
