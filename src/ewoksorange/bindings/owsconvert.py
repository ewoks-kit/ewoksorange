import warnings

from ..gui.workflows.owscheme import ewoks_to_ows  # noqa: F401
from ..gui.workflows.owscheme import graph_is_supported  # noqa: F401
from ..gui.workflows.owscheme import ows_to_ewoks  # noqa: F401
from ..gui.workflows.owscheme import patch_parse_ows_stream  # noqa: F401

__all__ = ["ows_to_ewoks", "ewoks_to_ows", "graph_is_supported"]

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.bridge.owscheme' module.",
    DeprecationWarning,
    stacklevel=2,
)
