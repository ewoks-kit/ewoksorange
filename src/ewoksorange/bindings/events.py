import warnings

from ..gui.utils.events import scheme_ewoks_events  # noqa F401

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.ewoks_utils.events' module.",
    DeprecationWarning,
    stacklevel=2,
)
