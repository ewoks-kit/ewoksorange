import warnings

from ewoksorange.gui.utils.invalid_data import INVALIDATION_DATA  # noqa: F401
from ewoksorange.gui.utils.invalid_data import as_invalidation  # noqa: F401
from ewoksorange.gui.utils.invalid_data import as_missing  # noqa: F401
from ewoksorange.gui.utils.invalid_data import is_invalid_data  # noqa: F401

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.invalid_data' module.",
    DeprecationWarning,
    stacklevel=2,
)
