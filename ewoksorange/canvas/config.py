from orangewidget.workflow import config as orangeconfig
from ewoksorange.registration import NATIVE_WIDGETS_PROJECT
import pkg_resources


class Config(orangeconfig.Config):
    @staticmethod
    def widgets_entry_points():
        """
        Return an `EntryPoint` iterator for all 'orange.widget' entry
        points.
        """
        # Ensure the 'this' distribution's ep is the first. iter_entry_points
        # yields them in unspecified order.
        all_eps = pkg_resources.iter_entry_points(NATIVE_WIDGETS_PROJECT + ".widgets")
        return iter(all_eps)

    @staticmethod
    def addon_entry_points():
        return Config.widgets_entry_points()
