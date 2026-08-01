from ._oasys_patch import oasys_patch
from .orange_utils.signal_manager import patch_signal_manager
from .owwidgets.summarizers import summarize  # noqa: F401
from .workflows.owscheme import patch_parse_ows_stream
from .workflows.owscheme import patch_scheme_load
from .workflows.owscheme import patch_scheme_to_etree

oasys_patch()
patch_parse_ows_stream()
patch_scheme_load()
patch_scheme_to_etree()
patch_signal_manager()
