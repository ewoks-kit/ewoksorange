import warnings

__all__ = ["execute_graph", "load_graph", "save_graph", "convert_graph"]

from .. import convert_graph
from .. import execute_graph
from .. import load_graph
from .. import save_graph

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.bindings' module.",
    DeprecationWarning,
    stacklevel=2,
)
