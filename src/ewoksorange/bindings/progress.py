import warnings

from ..gui.qt_utils.progress import QProgress  # noqa F401

__all__ = ["QProgress"]


warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.owwidgets.*' modules.",
    DeprecationWarning,
    stacklevel=2,
)
