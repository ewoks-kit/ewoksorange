import warnings

from ..gui.orange_utils.signal_manager import (  # noqa F401
    SignalManagerWithOutputTracking,
)
from ..gui.orange_utils.signal_manager import SignalManagerWithoutScheme  # noqa F401
from ..gui.orange_utils.signal_manager import SignalManagerWithScheme  # noqa F401
from ..gui.orange_utils.signal_manager import patch_signal_manager  # noqa F401

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui...' module.",
    DeprecationWarning,
    stacklevel=2,
)
