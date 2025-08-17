from .bindings.owsignal_manager import patch_signal_manager
from .oasys_patch import oasys_patch

oasys_patch()
patch_signal_manager()

__version__ = "1.1.0"
