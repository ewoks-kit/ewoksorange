import functools
import logging

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
    """Session-scoped Qt application for testing Orange-based Ewoks workflows."""
    from ewoksorange.gui.qt_utils.app import qtapp_context

    request.config.hook.pytest_ewoksorange_qtapp_setup()
    with qtapp_context() as app:
        assert app is not None
        yield app
    ewoksorange_qtapp_teardown(app)
    request.config.hook.pytest_ewoksorange_qtapp_teardown(app=app)


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
