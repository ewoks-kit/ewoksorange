from enum import Enum

_OrangeVersion = Enum("OrangeVersion", "latest oasys_fork")

try:
    import oasys.widgets  # noqa F401

    ORANGE_VERSION = _OrangeVersion.oasys_fork
except ImportError:
    ORANGE_VERSION = _OrangeVersion.latest
