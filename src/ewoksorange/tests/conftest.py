import functools
import gc
import logging
import warnings

import pytest

from orangecontrib.ewoksnowidget import global_cleanup_ewoksnowidget
from orangecontrib.ewokstest import enable_ewokstest_category

from ..gui.canvas.handler import OrangeCanvasHandler
from ..gui.qt_utils.app import get_all_qtwidgets
from ..gui.qt_utils.app import qtapp_context
from ..orange_version import ORANGE_VERSION

logger = logging.getLogger(__name__)


def global_cleanup_orange():
    if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
        pass
    else:
        from orangecanvas.document.suggestions import Suggestions

        Suggestions.instance = None


def global_cleanup_pytest():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for obj in gc.get_objects():
            if isinstance(obj, logging.LogRecord):
                obj.exc_info = None  # traceback keeps frames which keep locals


def collect_garbage(app):
    app.processEvents()
    while gc.collect():
        app.processEvents()


def safe_session_fixture(fixture):
    """Use instead of `pytest.fixture` to ensure the session fixture is executed only once."""
    return_value = None

    @functools.wraps(fixture)
    def wrapper(*args, **kw):
        nonlocal return_value

        if return_value is None:
            gen = fixture(*args, **kw)
            return_value = next(gen)
            try:
                yield return_value
            finally:
                try:
                    next(gen)
                except StopIteration:
                    pass
        else:
            yield return_value

    return pytest.fixture(scope="session")(wrapper)


@safe_session_fixture
def qtapp():
    enable_ewokstest_category()
    with qtapp_context() as app:
        assert app is not None
        yield app
    collect_garbage(app)
    global_cleanup_ewoksnowidget()
    global_cleanup_orange()
    global_cleanup_pytest()
    collect_garbage(app)
    warn_qtwidgets_alive()


@pytest.fixture(scope="session")
def raw_ewoks_orange_canvas(qtapp):
    with OrangeCanvasHandler() as handler:
        yield handler


@pytest.fixture()
def ewoks_orange_canvas(raw_ewoks_orange_canvas):
    yield raw_ewoks_orange_canvas
    try:
        raw_ewoks_orange_canvas.scheme.ewoks_finalize()
    except AttributeError:
        pass


def warn_qtwidgets_alive():
    widgets = get_all_qtwidgets()
    if widgets:
        logger.warning("%d remaining widgets after tests", len(widgets))
