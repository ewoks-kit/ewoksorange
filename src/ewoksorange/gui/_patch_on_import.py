from ._oasys_patch import oasys_patch
from .orange_utils.signal_manager import patch_signal_manager
from .owwidgets.summarizers import summarize  # noqa: F401
from .workflows.owscheme import patch_parse_ows_stream

oasys_patch()
patch_parse_ows_stream()
patch_signal_manager()
