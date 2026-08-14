import pytest


@pytest.hookspec()
def pytest_ewoksorange_qtapp_setup() -> None:
    """Called once, before the shared Qt application and widget registry are created.

    Implement this hook in a project's own conftest.py to run setup that must
    happen before Orange's widget discovery runs (e.g. enabling a hidden
    widget category used only by that project's own tests). Must be named
    with the `pytest_` prefix, like any other pytest hook implementation, or
    `PytestPluginManager` silently ignores it.
    """


@pytest.hookspec()
def pytest_ewoksorange_qtapp_teardown(app) -> None:
    """Called once, after the shared Qt application's own teardown has run.

    `app` is the `QApplication` the `ewoksorange_qtapp` fixture created (not
    yet torn down further), in case an implementation needs it (e.g. to
    process pending events as part of its own cleanup).

    Implement this hook in a project's own conftest.py to run teardown that
    is the counterpart of `pytest_ewoksorange_qtapp_setup` (e.g. undoing
    process-wide state set up before Orange's widget discovery). Must be
    named with the `pytest_` prefix, like any other pytest hook
    implementation, or `PytestPluginManager` silently ignores it.
    """
