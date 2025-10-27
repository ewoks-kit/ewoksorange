import warnings

from .widgets.data_viewer import DataViewer  # noqa F401

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.widgets.data_viewer' module.",
    DeprecationWarning,
    stacklevel=2,
)
