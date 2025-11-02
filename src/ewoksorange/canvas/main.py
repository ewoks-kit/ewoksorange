import warnings

from ..gui.canvas.main import main  # noqa F401

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.canvas.main' module.",
    DeprecationWarning,
    stacklevel=2,
)
