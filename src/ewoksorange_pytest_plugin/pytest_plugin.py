import functools
import logging
from contextlib import ExitStack

import pytest

from . import hookspecs
from .qtapp_teardown import ewoksorange_qtapp_teardown

# WARNING: defer importing Qt!

logger = logging.getLogger(__name__)


def pytest_addhooks(pluginmanager) -> None:
    pluginmanager.add_hookspecs(hookspecs)


def _safe_session_fixture(fixture):
    """Use instead of `pytest.fixture` to ensure the session fixture body is executed only once."""
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


@_safe_session_fixture
def ewoksorange_qtapp(request):
    """Session-scoped Qt application for testing Orange-based Ewoks workflows.

    Adopts a `QApplication` created earlier by e.g. `execute_graph(..., no_gui=True)`.
    """

    from ewoksorange.gui.qt_utils.app import close_qtapp
    from ewoksorange.gui.qt_utils.app import ensure_qtapp
    from ewoksorange.gui.qt_utils.app import get_qtapp

    request.config.hook.pytest_ewoksorange_qtapp_setup()
    ensure_qtapp()
    app = get_qtapp()
    assert app is not None, "Unable to ensure a QApplication"
    yield app

    # Called in reverse order, last one first.
    with ExitStack() as stack:
        stack.callback(request.config.hook.pytest_ewoksorange_qtapp_teardown, app=app)
        stack.callback(ewoksorange_qtapp_teardown, app)
        stack.callback(close_qtapp)


@pytest.fixture()
def orange_canvas_handler(ewoksorange_qtapp):
    """A fresh `OrangeCanvasHandler` for this test, for widget-level
    introspection that :code:`execute_graph(..., no_gui=True)` itself
    cannot provide:

        def test_something(orange_canvas_handler):
            result = execute_graph(
                graph, no_gui=True, orange_canvas_handler=orange_canvas_handler
            )
            widget = orange_canvas_handler.widget_from_id("2")
            ...
    """
    from ewoksorange.gui.canvas.handler import OrangeCanvasHandler

    with OrangeCanvasHandler() as handler:
        yield handler
