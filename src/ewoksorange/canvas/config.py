import warnings

from ..gui.canvas.config import Config  # noqa F401
from ..gui.canvas.config import widgets_entry_points  # noqa F401

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.canvas.config' module.",
    DeprecationWarning,
    stacklevel=2,
)
