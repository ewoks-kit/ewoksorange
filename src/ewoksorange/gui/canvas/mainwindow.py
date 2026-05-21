from orangecanvas.application.canvasmain import CanvasMainWindow as _CanvasMainWindow

from .schemeedit import SchemeEditWidget


class CanvasMainWindow(_CanvasMainWindow):

    EDITOR_WIDGET_CONSTRUCTOR = SchemeEditWidget
    # Redefining the 'EDITOR_WIDGET_CONSTRUCTOR' allow use to add features to the default 'SchemeEditWidget' like adding actions to the link.
