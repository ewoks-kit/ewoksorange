import warnings

from .gui.owwidgets.registration import get_owwidget_descriptions  # noqa F401
from .gui.owwidgets.registration import register_owwidget  # noqa F401
from .gui.owwidgets.registration import widget_discovery  # noqa F401

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.owwidgets.registration' module.",
    DeprecationWarning,
    stacklevel=2,
)
