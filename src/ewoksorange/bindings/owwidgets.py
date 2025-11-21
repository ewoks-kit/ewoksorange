# flake8-in-file-ignores:
import warnings

from ..gui.owwidgets.base import OWBaseWidget  # noqa: F401
from ..gui.owwidgets.base import OWEwoksBaseWidget  # noqa: F401
from ..gui.owwidgets.base import OWWidget  # noqa: F401
from ..gui.owwidgets.meta import ow_build_opts
from ..gui.owwidgets.nothread import OWEwoksWidgetNoThread
from ..gui.owwidgets.threaded import OWEwoksWidgetOneThread
from ..gui.owwidgets.threaded import OWEwoksWidgetOneThreadPerRun
from ..gui.owwidgets.threaded import OWEwoksWidgetWithTaskStack
from ..gui.owwidgets.types import is_ewoks_widget  # noqa: F401
from ..gui.owwidgets.types import is_ewoks_widget_class  # noqa: F401
from ..gui.owwidgets.types import is_native_widget  # noqa: F401
from ..gui.owwidgets.types import is_native_widget_class  # noqa: F401
from ..gui.owwidgets.types import is_orange_widget  # noqa: F401
from ..gui.owwidgets.types import is_orange_widget_class  # noqa: F401
from ..gui.utils import invalid_data  # noqa: F401

__all__ = [
    "OWEwoksWidgetNoThread",
    "OWEwoksWidgetOneThread",
    "OWEwoksWidgetOneThreadPerRun",
    "OWEwoksWidgetWithTaskStack",
    "ow_build_opts",
]

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.owwidgets.*' modules.",
    DeprecationWarning,
    stacklevel=2,
)
