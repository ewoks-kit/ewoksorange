import warnings

import pytest

from orangecontrib.ewokstest import enable_ewokstest_category

from ..gui.canvas.menu import patch_canvas_main_window

pytest.register_assert_rewrite("ewoksorange.tests.executor.signals")


def pytest_ewoksorange_qtapp_setup() -> None:
    enable_ewokstest_category()


@pytest.fixture(scope="session")
def qtapp(ewoksorange_qtapp):
    warnings.warn(
        "The 'qtapp' fixture is deprecated. Use 'ewoksorange_qtapp' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    yield ewoksorange_qtapp


@pytest.fixture()
def raw_ewoks_orange_canvas(orange_canvas_handler):
    warnings.warn(
        "The 'raw_ewoks_orange_canvas' fixture is deprecated. Use "
        "'ewoksorange.bindings.execute_graph(..., no_gui=True)' to run a workflow "
        "optionally with the 'orange_canvas_handler' fixture for "
        "widget-level introspection.",
        DeprecationWarning,
        stacklevel=2,
    )
    yield orange_canvas_handler


@pytest.fixture()
def ewoks_orange_canvas(raw_ewoks_orange_canvas):
    warnings.warn(
        "The 'ewoks_orange_canvas' fixture is deprecated. Use "
        "'ewoksorange.bindings.execute_graph(..., no_gui=True)' to run a workflow "
        "optionally with the 'orange_canvas_handler' fixture for "
        "widget-level introspection.",
        DeprecationWarning,
        stacklevel=2,
    )
    yield raw_ewoks_orange_canvas


@pytest.fixture()
def patched_canvas_main_window():
    patch_canvas_main_window()


@pytest.fixture()
def orange_canvas_handler(patched_canvas_main_window, orange_canvas_handler):
    """The canvas of all tests is patched as in `ewoksorange.gui.canvas.main`,
    whatever the order of the tests. The patch is done before the plugin fixture
    creates the canvas window."""
    yield orange_canvas_handler
