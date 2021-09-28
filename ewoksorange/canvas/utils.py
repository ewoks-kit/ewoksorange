from typing import Optional

try:
    OBSOLETE_ORANGE = False
    from Orange.canvas.mainwindow import MainWindow
except ImportError:
    OBSOLETE_ORANGE = True
    from Orange.canvas.application.canvasmain import CanvasMainWindow as MainWindow
from ..bindings.qtapp import get_qtapp


def get_orange_canvas() -> Optional[MainWindow]:
    app = get_qtapp()
    if app is None:
        return None
    for widget in app.topLevelWidgets():
        if isinstance(widget, MainWindow):
            return widget
    return None
