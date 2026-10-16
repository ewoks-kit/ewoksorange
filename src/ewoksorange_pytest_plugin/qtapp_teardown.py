import gc
import logging
import warnings
from contextlib import ExitStack

# WARNING: defer importing Qt!

logger = logging.getLogger(__name__)


def _global_cleanup_orange() -> None:
    from orangecanvas.document.suggestions import Suggestions

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


def _delete_python_owned_qobjects(app) -> None:
    """Delete the remaining Qt objects that are owned by Python and have no parent."""
    from AnyQt import sip
    from AnyQt.QtCore import QObject

    # Otherwise PyQt destroys them while the interpreter exits, which crashes
    # randomly on Windows.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for obj in gc.get_objects():
            # No attribute access on `obj`: some objects do not allow it,
            # e.g. `isinstance` accesses `__class__`.
            if not issubclass(type(obj), QObject) or obj is app:
                continue
            if sip.isdeleted(obj) or not sip.ispyowned(obj):
                continue
            if QObject.parent(obj) is not None:
                continue
            sip.delete(obj)
    app.processEvents()


def _warn_qtwidgets_alive() -> None:
    from ewoksorange.gui.qt_utils.app import get_all_qtwidgets

    widgets = get_all_qtwidgets()
    if widgets:
        logger.warning("%d remaining widgets after tests", len(widgets))


def ewoksorange_qtapp_teardown(app) -> None:
    """Counterpart of `ewoksorange_qtapp`'s setup: run once, after the test
    session's Qt application is done, to release process-wide state before
    the `pytest_ewoksorange_qtapp_teardown` hook fires.
    """
    # Called in reverse order, last one first.
    with ExitStack() as stack:
        stack.callback(_delete_python_owned_qobjects, app)
        stack.callback(_warn_qtwidgets_alive)
        stack.callback(_collect_garbage, app)
        stack.callback(_global_cleanup_pytest)
        stack.callback(_global_cleanup_orange)
        stack.callback(_global_cleanup_ewoksnowidget)
        stack.callback(_collect_garbage, app)
