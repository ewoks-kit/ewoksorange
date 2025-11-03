from typing import Optional

from ...orange_version import ORANGE_VERSION

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    from oasys.canvas.mainwindow import OASYSMainWindow as OWCanvasMainWindow
elif ORANGE_VERSION == ORANGE_VERSION.latest_orange:
    from Orange.canvas.mainwindow import MainWindow as OWCanvasMainWindow
else:
    # from orangewidget.workflow.mainwindow import OWCanvasMainWindow # ewoks-canvas CLI does not use this
    from orangecanvas.application.canvasmain import (
        CanvasMainWindow as OWCanvasMainWindow,
    )

from ..qt_utils.app import get_qtapp


def get_orange_canvas() -> Optional[OWCanvasMainWindow]:
    """Get the QApplication in the current process (if any)."""
    app = get_qtapp()
    if app is None:
        return None
    for widget in app.topLevelWidgets():
        if isinstance(widget, OWCanvasMainWindow):
            return widget
    return None
