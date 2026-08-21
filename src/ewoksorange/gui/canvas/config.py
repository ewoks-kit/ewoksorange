"""Copy parts of Orange.canvas.config to be used when Orange3 is not installed."""

from typing import Tuple

from ... import pkg_meta
from ...orange_version import ORANGE_VERSION

if ORANGE_VERSION == ORANGE_VERSION.latest_oasys:
    from oasys2.canvas.config import WIDGETS_ENTRY  # "oasys2.widgets"
    from oasys2.canvas.config import OasysConfig as _Config

    # Unlike Orange, OASYS2 defines a group for example workflows.
    EXAMPLE_WORKFLOWS_ENTRY = "oasys2.tutorials"
elif ORANGE_VERSION == ORANGE_VERSION.latest_orange:
    from Orange.canvas.config import WIDGETS_ENTRY  # "orange.widgets"
    from Orange.canvas.config import Config as _Config

    EXAMPLE_WORKFLOWS_ENTRY = WIDGETS_ENTRY + ".tutorials"
else:
    from orangewidget.workflow.config import WIDGETS_ENTRY  # "orange.widgets"
    from orangewidget.workflow.config import Config as _Config

    EXAMPLE_WORKFLOWS_ENTRY = WIDGETS_ENTRY + ".tutorials"


class Config(_Config):
    if ORANGE_VERSION == ORANGE_VERSION.latest_oasys:
        # OASYS2 inherits the module-globals based discovery of
        # orange-canvas-core, which cannot describe Ewoks widgets.
        @staticmethod
        def widget_discovery(*args, **kwargs):
            """Return a class-based Orange widget discovery object."""
            from orangewidget.workflow.discovery import WidgetDiscovery

            return WidgetDiscovery(*args, **kwargs)

    @staticmethod
    def widgets_entry_points() -> Tuple[pkg_meta.EntryPoint]:
        """Return all WIDGETS_ENTRY entry points."""
        # Ensure 'this' distribution's ep is the first.
        # `entry_points` returns them in unspecified order.
        from orangecontrib.ewokstest import is_ewokstest_category_enabled

        eps = list()
        for ep in pkg_meta.entry_points(WIDGETS_ENTRY):
            if (
                _get_ep_module(ep) == "orangecontrib.ewokstest"
                and not is_ewokstest_category_enabled()
            ):
                continue
            eps.append(ep)
        return tuple(eps)

    @staticmethod
    def examples_entry_points() -> Tuple[pkg_meta.EntryPoint]:
        """Return all EXAMPLE_WORKFLOWS_ENTRY entry points."""
        from orangecontrib.ewokstest import is_ewokstest_category_enabled

        eps = list()
        for ep in pkg_meta.entry_points(EXAMPLE_WORKFLOWS_ENTRY):
            if (
                _get_ep_module(ep) == "orangecontrib.ewokstest.tutorials"
                and not is_ewokstest_category_enabled()
            ):
                continue
            eps.append(ep)
        return tuple(eps)

    tutorials_entry_points = examples_entry_points


def _get_ep_module(ep) -> str:
    try:
        return ep.module
    except AttributeError:
        return ep.module_name


def widgets_entry_points():
    return Config.widgets_entry_points()
