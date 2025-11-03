import warnings

from ewoksorange.gui.orange_utils.settings import Setting  # noqa: F401
from ewoksorange.gui.orange_utils.settings import get_settings  # noqa: F401
from ewoksorange.gui.orange_utils.settings import is_setting  # noqa: F401

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.orange_utils.owsettings' module.",
    DeprecationWarning,
    stacklevel=2,
)
