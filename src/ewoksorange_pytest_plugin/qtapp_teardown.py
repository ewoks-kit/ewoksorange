import gc
import logging
import warnings
from contextlib import ExitStack

from ewoksorange.gui.qt_utils.app import get_all_qtwidgets

logger = logging.getLogger(__name__)


def _global_cleanup_orange() -> None:
    try:
        from orangecanvas.document.suggestions import Suggestions
    except ModuleNotFoundError:
        # Not present in the oasys-canvas-core fork of orange-canvas-core.
        return

    Suggestions.instance = None


def _global_cleanup_ewoksnowidget() -> None:
    from orangecontrib.ewoksnowidget import global_cleanup_ewoksnowidget

    global_cleanup_ewoksnowidget()


def _global_cleanup_pytest() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for obj in gc.get_objects():
            if isinstance(obj, logging.LogRecord):
                obj.exc_info = None  # traceback keeps frames which keep locals


def _collect_garbage(app) -> None:
    app.processEvents()
    while gc.collect():
        app.processEvents()


def _warn_qtwidgets_alive() -> None:
    widgets = get_all_qtwidgets()
    if widgets:
        logger.warning("%d remaining widgets after tests", len(widgets))


def ewoksorange_qtapp_teardown(app) -> None:
    """Counterpart of `ewoksorange_qtapp`'s setup: run once, after the test
    session's Qt application is done, to release process-wide state before
    the `pytest_ewoksorange_qtapp_teardown` hook fires.
    """
    with ExitStack() as stack:
        stack.callback(_warn_qtwidgets_alive)
        stack.callback(_collect_garbage, app)
        stack.callback(_global_cleanup_pytest)
        stack.callback(_global_cleanup_orange)
        stack.callback(_global_cleanup_ewoksnowidget)
        stack.callback(_collect_garbage, app)
