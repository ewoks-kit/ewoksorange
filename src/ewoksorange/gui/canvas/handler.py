import logging
import os
import time
from typing import Dict

from AnyQt import QtWidgets
from AnyQt.QtCore import Qt

from ...orange_version import ORANGE_VERSION

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    from oasys.canvas import conf as orangeconfig
    from oasys.canvas.mainwindow import OASYSMainWindow as _OWCanvasMainWindow
    from orangecanvas import config as canvasconfig
    from orangecanvas.registry import set_global_registry
    from orangecanvas.registry.qt import QtWidgetRegistry

    class OWCanvasMainWindow(_OWCanvasMainWindow):
        def show_scheme_properties_for(self, scheme, window_title=None):
            return QtWidgets.QDialog.Accepted

    try:
        from oasys.canvas.mainwindow import _MainWindowRegistry
    except ImportError:
        _MainWindowRegistry = None

else:
    from orangecanvas import config as canvasconfig
    from orangecanvas.registry import set_global_registry
    from orangecanvas.registry.qt import QtWidgetRegistry

    if ORANGE_VERSION == ORANGE_VERSION.latest_orange:
        from Orange.canvas import config as orangeconfig
        from Orange.canvas.mainwindow import MainWindow as OWCanvasMainWindow
    else:
        # from orangewidget.workflow.mainwindow import OWCanvasMainWindow  # ewoks-canvas CLI does not use this
        from orangecanvas.application.canvasmain import (
            CanvasMainWindow as OWCanvasMainWindow,
        )
        from . import config as orangeconfig

from ..orange_utils.signal_manager import SignalManagerWithOutputTracking
from ..owwidgets.base import OWEwoksBaseWidget
from ..qt_utils import app as qt_app
from ..workflows.representation import ows_file_context
from .utils import get_orange_canvas

_logger = logging.getLogger(__name__)


class OrangeCanvasHandler:
    """Run orange widget-based workflow manually (i.e. without executing the Qt application)"""

    def __init__(self):
        self.canvas = get_orange_canvas()
        self.__is_owner = self.canvas is None

    def __del__(self):
        self.close()

    def __enter__(self):
        if self.canvas is None:
            self._init_canvas()
            self.__is_owner = True
        return self

    def __exit__(self, *_):
        self.close()

    def _init_canvas(self):
        qt_app.ensure_qtapp()

        widget_registry = QtWidgetRegistry()
        set_global_registry(widget_registry)

        if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
            config = orangeconfig.oasysconf()
            config.init()
            canvasconfig.set_default(config)
            widget_discovery = config.widget_discovery(widget_registry)
            widget_discovery.run(config.widgets_entry_points())
        else:
            config = orangeconfig.Config()
            config.init()
            canvasconfig.set_default(config)
            widget_discovery = config.widget_discovery(widget_registry)
            widget_discovery.run(orangeconfig.widgets_entry_points())

        canvas = OWCanvasMainWindow()
        canvas.setAttribute(Qt.WA_DeleteOnClose)
        canvas.set_widget_registry(widget_registry)  # makes a copy of the registry

        if (
            ORANGE_VERSION == ORANGE_VERSION.oasys_fork
            and _MainWindowRegistry is not None
        ):
            _MainWindowRegistry.Instance().register_instance(
                instance=canvas, application_name=str(os.getpid())
            )  # need it for finding the canvas from the widgets

        self.canvas = canvas
        self.process_events()

    def close(self, force=False):
        if self.canvas is None or (not self.__is_owner and not force):
            return
        canvas, self.canvas = self.canvas, None
        self.process_events()
        # do not prompt for saving modification:
        canvas.current_document().setModified(False)
        canvas.close()
        self.process_events()

    def load_graph(self, graph, **kwargs):
        with ows_file_context(graph, **kwargs) as filename:
            self.load_ows(filename)

    def load_ows(self, filename: str):
        self.canvas.load_scheme(filename)

    @property
    def scheme(self):
        return self.canvas.current_document().scheme()

    @property
    def signal_manager(self) -> SignalManagerWithOutputTracking:
        signal_manager = self.scheme.signal_manager
        assert isinstance(
            signal_manager, SignalManagerWithOutputTracking
        ), "Orange signal manager was not patched before instantiated"
        return signal_manager

    def iter_nodes(self):
        for node in self.scheme.nodes:
            yield node

    def process_events(self):
        qt_app.process_qtapp_events()

    def show(self):
        qt_app.process_qtapp_events()
        self.canvas.show()
        qt_app.get_qtapp().exec()

    def widgets_from_name(self, name: str):
        for node in self.iter_nodes():
            if node.title == name:
                yield self.scheme.widget_for_node(node)

    def widget_from_id(self, id: str):
        return self.scheme.widget_for_node(self.scheme.nodes[int(id)])

    def iter_widgets(self):
        for node in self.iter_nodes():
            yield self.scheme.widget_for_node(node)

    def iter_widgets_with_name(self):
        for node in self.iter_nodes():
            yield node.title, self.scheme.widget_for_node(node)

    def iter_output_values(self):
        for name, widget in self.iter_widgets_with_name():
            yield name, widget.get_task_output_values()

    def get_output_values(self) -> Dict[str, dict]:
        return dict(self.iter_output_values())

    def set_input_values(self, inputs: Dict[str, dict]) -> None:
        for name, widget in self.iter_widgets_with_name():
            for adict in inputs:
                if adict["label"] == name:
                    widget.update_default_inputs(**{adict["name"]: adict["value"]})

    def start_workflow(self):
        triggered = False
        for node in self.iter_nodes():
            if not any(self.scheme.find_links(sink_node=node)):
                widget = self.scheme.widget_for_node(node)
                triggered = True
                _logger.debug("Trigger workflow node %r", node.title)
                widget.handleNewSignals()
        if not triggered:
            _logger.warning("This workflow has no widgets that can be triggered")

    def wait_widgets(self, timeout=None, raise_error: bool = True):
        """Wait for all widgets to be "finished". Widget failures are re-raised."""
        signal_manager = self.signal_manager
        widgets = list(self.iter_widgets())
        t0 = time.time()

        while True:
            self.process_events()
            finished = list()
            exceptions = dict()
            for widget in widgets:
                is_finished = signal_manager.widget_is_finished(widget)
                if raise_error and isinstance(widget, OWEwoksBaseWidget):
                    exception = widget.task_exception or widget.post_task_exception
                    if exception is not None:
                        if is_finished:
                            raise exception
                        else:
                            exceptions[widget] = exception
                finished.append(is_finished)
            if all(finished):
                if exceptions:
                    raise next(iter(exceptions.values()))
                break
            if timeout is not None:
                if (time.time() - t0) > timeout:
                    if exceptions:
                        raise next(iter(exceptions.values()))
                    raise TimeoutError(timeout)
            time.sleep(0.1)
