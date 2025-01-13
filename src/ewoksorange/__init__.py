from .bindings import load_graph  # noqa: F401
from .bindings import save_graph  # noqa: F401
from .bindings import convert_graph  # noqa: F401
from .bindings import execute_graph  # noqa: F401
from .bindings import graph_is_supported  # noqa: F401
from .bindings.owsignal_manager import patch_signal_manager
from .oasys_patch import oasys_patch

oasys_patch()
patch_signal_manager()

__version__ = "1.1.0"
