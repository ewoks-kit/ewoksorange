import warnings

from .widgets.parameter_form import ParameterForm  # noqa F401
from .widgets.parameter_form import block_signals  # noqa F401

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.widgets.parameter_form' module.",
    DeprecationWarning,
    stacklevel=2,
)
