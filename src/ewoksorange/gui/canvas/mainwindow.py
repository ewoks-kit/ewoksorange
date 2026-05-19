from orangecanvas.application.canvasmain import CanvasMainWindow as _CanvasMainWindow
from .schemeedit import SchemeEditWidget


class CanvasMainWindow(_CanvasMainWindow):

    EDITOR_WIDGET_CONSTRUCTOR = SchemeEditWidget
