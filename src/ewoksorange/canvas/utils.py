import warnings

from ..gui.canvas.utils import get_orange_canvas  # noqa F401

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.canvas.utils' module.",
    DeprecationWarning,
    stacklevel=2,
)
