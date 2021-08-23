import pytest
from ewoksorange.registration import register_addon_package
from ewoksorange.bindings.qtapp import ensure_qtapp
from .examples import ewoks_example_1_addon
from .examples import ewoks_example_2_addon


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
    APP = ensure_qtapp()
    yield
    APP.exit()
