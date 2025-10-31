import warnings

from .qt_utils.qt_signals import block_signals  # noqa F401

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.widgets.qt_signals' module.",
    DeprecationWarning,
    stacklevel=2,
)
