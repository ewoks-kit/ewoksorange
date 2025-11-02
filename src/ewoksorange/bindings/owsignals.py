import warnings

from ..gui.orange_utils.signals import get_ewoks_to_orange_mapping  # noqa F401
from ..gui.orange_utils.signals import get_input_names  # noqa F401
from ..gui.orange_utils.signals import get_orange_to_ewoks_mapping  # noqa F401
from ..gui.orange_utils.signals import get_output_names  # noqa F401
from ..gui.orange_utils.signals import get_signal_container  # noqa F401
from ..gui.orange_utils.signals import get_signals  # noqa F401
from ..gui.orange_utils.signals import is_signal  # noqa F401
from ..gui.orange_utils.signals import signal_ewoks_to_orange_name  # noqa F401
from ..gui.orange_utils.signals import signal_orange_to_ewoks_name  # noqa F401
from ..gui.orange_utils.signals import validate_inputs  # noqa F401
from ..gui.orange_utils.signals import validate_outputs  # noqa F401

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui...' module.",
    DeprecationWarning,
    stacklevel=2,
)
