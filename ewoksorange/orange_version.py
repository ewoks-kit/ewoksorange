from enum import Enum

_OrangeVersion = Enum("OrangeVersion", "latest henri_fork")
ORANGE_VERSION = _OrangeVersion.latest

try:
    from Orange.widgets.widget import OWBaseWidget  # noqa F401
except ImportError:
    ORANGE_VERSION = _OrangeVersion.henri_fork
