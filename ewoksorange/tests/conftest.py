import logging
import pytest
from ewoksorange.registration import register_addon_package
from ewoksorange.bindings.qtapp import qtapp_context
from ewoksorange.bindings.qtapp import get_all_qtwidgets
from ewoksorange.canvas.handler import OrangeCanvasHandler
from .examples import ewoks_example_1_addon
from .examples import ewoks_example_2_addon


logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def register_ewoks_example_1_addon():
    register_addon_package(ewoks_example_1_addon)
    yield


@pytest.fixture(scope="session")
def register_ewoks_example_2_addon():
    register_addon_package(ewoks_example_2_addon)
    yield


@pytest.fixture(scope="session")
def register_ewoks_example_addons(
    register_ewoks_example_1_addon, register_ewoks_example_2_addon
):
    yield


@pytest.fixture(scope="session")
def qtapp():
    with qtapp_context() as app:
        yield app
    warn_qtwidgets_alive()


@pytest.fixture(scope="session")
def ewoks_orange_canvas(qtapp, register_ewoks_example_addons):
    with OrangeCanvasHandler() as handler:
        yield handler


def warn_qtwidgets_alive():
    widgets = get_all_qtwidgets()
    if widgets:
        logger.warning(
            "%d remaining widgets after tests:\n %s",
            len(widgets),
            "\n ".join(map(str, widgets)),
        )
