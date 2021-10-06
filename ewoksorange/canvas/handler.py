import time
from AnyQt.QtCore import Qt

try:
    OBSOLETE_ORANGE = False
    from Orange.canvas.mainwindow import MainWindow
    from orangecanvas.registry.qt import QtWidgetRegistry
    from Orange.canvas import config as orangeconfig
    from orangecanvas import config as canvasconfig
except ImportError:
    OBSOLETE_ORANGE = True
    from Orange.canvas.application.canvasmain import CanvasMainWindow as MainWindow
    from Orange.canvas.registry.qt import QtWidgetRegistry
    from Orange.canvas.registry.qt import QtWidgetDiscovery
    from Orange.canvas import config as orangeconfig
    import Orange.canvas.canvas.items.nodeitem

    # QWaiterThread is not always stopped before garbage collection
    Orange.canvas.canvas.items.nodeitem.has_silx = False


from ..bindings import qtapp


def default_widget_is_ready(widget):
    return bool(widget.task_outputs)


class OrangeCanvasHandler:
    """Orange canvas handler intended for the test suite"""

    def __init__(self):
        self.canvas = None
        self._init_canvas()

    def _init_canvas(self):
        qtapp.ensure_qtapp()

        widget_registry = QtWidgetRegistry()
        if OBSOLETE_ORANGE:
            config = orangeconfig  # a module
            widget_discovery = QtWidgetDiscovery()
            widget_discovery.found_category.connect(widget_registry.register_category)
            widget_discovery.found_widget.connect(widget_registry.register_widget)
        else:
            config = orangeconfig.Config()  # an object module
            config.init()
            canvasconfig.set_default(config)
            widget_discovery = config.widget_discovery(widget_registry)
        widget_discovery.run(orangeconfig.widgets_entry_points())

        canvas = MainWindow()
        canvas.setAttribute(Qt.WA_DeleteOnClose)
        # set_global_registry(widget_registry)
        canvas.set_widget_registry(widget_registry)  # make a copy of the registry
        self.canvas = canvas
        self.process_events()

    def __enter__(self):
        if self.canvas is None:
            self._init_canvas()
        return self

    def __exit__(self, *args):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        if self.canvas is not None:
            canvas, self.canvas = self.canvas, None
            self.process_events()
            # do not prompt for saving modification:
            canvas.current_document().setModified(False)
            canvas.close()
            self.process_events()

    def load_ows(self, filename: str):
        self.canvas.load_scheme(filename)

    @property
    def scheme(self):
        return self.canvas.current_document().scheme()

    def process_events(self):
        qtapp.process_qtapp_events()

    def show(self):
        qtapp.process_qtapp_events()
        self.canvas.show()
        qtapp.get_qtapp().exec()

    def widgets_from_name(self, name: str):
        scheme = self.scheme
        for node in scheme.nodes:
            if node.title == name:
                yield self.scheme.widget_for_node(node)

    def all_widgets(self):
        scheme = self.scheme
        for node in scheme.nodes:
            yield self.scheme.widget_for_node(node)

    def wait_widgets(self, timeout=None, widget_is_ready=default_widget_is_ready):
        widgets = list(self.all_widgets())
        t0 = time.time()
        while any(not widget_is_ready(widget) for widget in widgets):
            self.process_events()
            if timeout is not None and (time.time() - t0) > timeout:
                raise TimeoutError()
            time.sleep(0.1)
