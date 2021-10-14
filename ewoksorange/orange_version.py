from enum import Enum

_OrangeVersion = Enum("OrangeVersion", "latest henri_fork oasys_fork")

try:
    import oasys.widgets  # noqa F401

    ORANGE_VERSION = _OrangeVersion.oasys_fork
except ImportError:
    try:
        from Orange.widgets.widget import OWBaseWidget  # noqa F401

        ORANGE_VERSION = _OrangeVersion.latest
    except ImportError:
        ORANGE_VERSION = _OrangeVersion.henri_fork
