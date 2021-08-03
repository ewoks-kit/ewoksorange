import pytest
from ewoksorange.registration import register_addon_package
from .examples import ewoks_example_1_addon
from .examples import ewoks_example_2_addon


@pytest.fixture(scope="session")
def register_ewoks_example_addons():
    register_addon_package(ewoks_example_1_addon)
    register_addon_package(ewoks_example_2_addon)
    yield
