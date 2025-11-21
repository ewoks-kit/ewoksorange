import warnings

from ..gui.qt_utils.app import QtEvent  # noqa F401
from ..gui.qt_utils.app import close_qtapp  # noqa F401
from ..gui.qt_utils.app import ensure_qtapp  # noqa F401
from ..gui.qt_utils.app import get_all_qtwidgets  # noqa F401
from ..gui.qt_utils.app import get_qtapp  # noqa F401
from ..gui.qt_utils.app import process_qtapp_events  # noqa F401
from ..gui.qt_utils.app import qt_message_handler  # noqa F401
from ..gui.qt_utils.app import qtapp_context  # noqa F401

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.qt_utils.qtapp' module.",
    DeprecationWarning,
    stacklevel=2,
)
