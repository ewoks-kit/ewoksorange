"""Copy parts of Orange.canvas.config to be used when Orange3 is not installed.
"""

from orangewidget.workflow.config import Config as _Config
from orangewidget.workflow.config import WIDGETS_ENTRY

from ..pkg_meta import iter_entry_points


class Config(_Config):
    @staticmethod
    def widgets_entry_points():
        """
        Return an `EntryPoint` iterator for all 'orange.widget' entry
        points.
        """
        # Ensure the 'this' distribution's ep is the first. iter_entry_points
        # yields them in unspecified order.
        return iter_entry_points(group=WIDGETS_ENTRY)

    @staticmethod
    def addon_entry_points():
        return Config.widgets_entry_points()


def widgets_entry_points():
    return Config.widgets_entry_points()
