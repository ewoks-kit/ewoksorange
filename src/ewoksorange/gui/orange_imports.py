import warnings

from ..gui.owwidgets.orange_imports import Input  # noqa F401
from ..gui.owwidgets.orange_imports import Output  # noqa F401
from ..gui.owwidgets.orange_imports import Setting  # noqa F401
from ..gui.widgets.orange_imports import gui  # noqa F401

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.owwidgets.orange_imports' or "
    " 'ewoksorange.gui.widgets.orange_imports' module.",
    DeprecationWarning,
    stacklevel=2,
)
