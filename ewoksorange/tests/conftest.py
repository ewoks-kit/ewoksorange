import pytest
from ewoksorange.registration import register_addon_package
from .examples import ewoks_example_addon


@pytest.fixture
def register_ewoks_example_addon():
    register_addon_package(ewoks_example_addon)
    yield
