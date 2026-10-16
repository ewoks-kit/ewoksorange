import io
import logging
import os
import tempfile
from pathlib import Path

from AnyQt.QtWidgets import QAction
from AnyQt.QtWidgets import QFileDialog
from AnyQt.QtWidgets import QMenu
from orangecanvas.application.canvasmain import CanvasMainWindow

from ..workflows.owscheme import ewoks_to_ows
from ..workflows.owscheme import ows_to_ewoks

_logger = logging.getLogger(__name__)
_FILTER = "Ewoks workflow (*.json *.yml *.yaml)"
_patched = False


def _import_ewoks_workflow(window: CanvasMainWindow) -> None:

    from ...bindings import load_graph  # Lazy import to avoid circular import

    filename, _ = QFileDialog.getOpenFileName(
        window, "Import Ewoks workflow", "", _FILTER
    )
    if not filename:
        return
    try:
        graph = load_graph(filename)
        with tempfile.TemporaryDirectory() as tmpdir:
            ows = os.path.join(tmpdir, "imported.ows")
            ewoks_to_ows(graph, ows, error_on_duplicates=False)
            # Opens in this window if it is empty, else in a new one,
            # without associating the temporary path with the document.
            window.open_example_scheme(ows)
    except Exception as e:
        _logger.exception("Ewoks import failed")
        window.output_view().write(f"Ewoks import failed: {e}\n")


def _export_ewoks_workflow(window: CanvasMainWindow) -> None:

    from ...bindings import save_graph  # Lazy import to avoid circular import

    filename, _ = QFileDialog.getSaveFileName(
        window, "Export Ewoks workflow", "", _FILTER
    )
    if not filename:
        return
    if not Path(filename).suffix:
        filename += ".json"
    try:
        scheme = window.current_document().scheme()
        buffer = io.BytesIO()
        scheme.save_to(buffer, pretty=True, pickle_fallback=True)
        buffer.seek(0)
        graph = ows_to_ewoks(buffer)
        save_graph(graph, filename)
    except Exception as e:
        _logger.exception("Ewoks export failed")
        window.output_view().write(f"Ewoks export failed: {e}\n")


def _add_actions(window: CanvasMainWindow) -> None:
    menu = window.menuBar().findChild(QMenu, "file-menu")
    if menu is None:
        return
    import_action = QAction(
        "Import Ewoks workflow...", window, objectName="action-import-ewoks"
    )
    import_action.triggered.connect(lambda: _import_ewoks_workflow(window))
    export_action = QAction(
        "Export Ewoks workflow...", window, objectName="action-export-ewoks"
    )
    export_action.triggered.connect(lambda: _export_ewoks_workflow(window))

    before = menu.findChild(QAction, "open-actions-separator")
    for action in (import_action, export_action):
        if before is not None:
            menu.insertAction(before, action)
        else:
            menu.addAction(action)


def add_ewoks_import_export_actions() -> None:
    """
    Add Ewoks import/export to the File menu of every canvas window.
    """
    global _patched
    if _patched:
        return
    _patched = True

    # CanvasMainWindow is instantiated both in Orange3 or in Oasys2 and there is no public interface given.
    original_init = CanvasMainWindow.__init__

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _add_actions(self)

    CanvasMainWindow.__init__ = __init__
