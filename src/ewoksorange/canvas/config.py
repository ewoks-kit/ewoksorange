"""Copy parts of Orange.canvas.config to be used when Orange3 is not installed.
"""

from ..orange_version import ORANGE_VERSION

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    from oasys.canvas.conf import oasysconf as _Config
    from oasys.canvas.conf import WIDGETS_ENTRY  # "oasys.widgets"
elif ORANGE_VERSION == ORANGE_VERSION.latest_orange:
    from Orange.canvas.config import Config as _Config
    from Orange.canvas.config import WIDGETS_ENTRY  # "orange.widgets"
else:
    from orangewidget.workflow.config import Config as _Config
    from orangewidget.workflow.config import WIDGETS_ENTRY  # "orange.widgets"

from ..pkg_meta import iter_entry_points

EXAMPLE_WORKFLOWS_ENTRY = WIDGETS_ENTRY + ".tutorials"


class Config(_Config):
    @staticmethod
    def widgets_entry_points():
        """Return an `EntryPoint` iterator for all WIDGETS_ENTRY entry points."""
        # Ensure the 'this' distribution's ep is the first. iter_entry_points
        # yields them in unspecified order.
        from orangecontrib.ewokstest import is_ewokstest_category_enabled

        for ep in iter_entry_points(group=WIDGETS_ENTRY):
            if (
                _get_ep_module(ep) == "orangecontrib.ewokstest"
                and not is_ewokstest_category_enabled()
            ):
                continue
            yield ep

    @staticmethod
    def examples_entry_points():
        """Return an `EntryPoint` iterator for all EXAMPLE_WORKFLOWS_ENTRY entry points."""
        from orangecontrib.ewokstest import is_ewokstest_category_enabled

        for ep in iter_entry_points(group=EXAMPLE_WORKFLOWS_ENTRY):
            if (
                _get_ep_module(ep) == "orangecontrib.ewokstest.tutorials"
                and not is_ewokstest_category_enabled()
            ):
                continue
            yield ep

    tutorials_entry_points = examples_entry_points


def _get_ep_module(ep) -> str:
    try:
        return ep.module
    except AttributeError:
        return ep.module_name


def widgets_entry_points():
    return Config.widgets_entry_points()
