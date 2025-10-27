from ._oasys_patch import oasys_patch
from .bindings.owsconvert import patch_parse_ows_stream
from .bindings.owsignal_manager import patch_signal_manager
from .gui.owwidgets.summarizers import summarize  # noqa: F401

oasys_patch()
patch_parse_ows_stream()
patch_signal_manager()
