import io
import logging
import os
import tempfile
from pathlib import Path

from AnyQt.QtWidgets import QAction
from AnyQt.QtWidgets import QFileDialog
from AnyQt.QtWidgets import QMenu
from orangecanvas.application.canvasmain import CanvasMainWindow
from orangecanvas.gui.utils import message_warning

from ..workflows.owscheme import ewoks_to_ows
from ..workflows.owscheme import ows_to_ewoks
from ..workflows.owscheme import update_ewoks_graph_attrs
from ..workflows.requirements import add_requirements

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
        try:
            add_requirements(graph)
        except Exception:
            graph.graph.graph.pop("requirements", None)
            _requirements_warning(window, "exported")
        save_graph(graph, filename)
    except Exception as e:
        _logger.exception("Ewoks export failed")
        window.output_view().write(f"Ewoks export failed: {e}\n")


def _requirements_warning(window: CanvasMainWindow, action: str) -> None:
    _logger.warning("Failed to generate the workflow requirements", exc_info=True)
    message_warning(
        "Failed to generate the requirements of the current Python environment. "
        f"The workflow is {action} without requirements.",
        title="Workflow requirements",
        exc_info=True,
        parent=window,
    )


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


def patch_canvas_main_window() -> None:
    """
    Add Ewoks import/export to the File menu of every canvas window, and
    generate the workflow requirements when a workflow is saved.
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

    # "File > Save" and "File > Save As". Not in `scheme_to_etree` which also
    # serializes the scheme on every edit (recovery file) and on copy.
    original_save_scheme_to = CanvasMainWindow.save_scheme_to

    def save_scheme_to(self, scheme, filename):
        try:
            update_ewoks_graph_attrs(scheme)
        except Exception:
            _requirements_warning(self, "saved")
        return original_save_scheme_to(self, scheme, filename)

    CanvasMainWindow.save_scheme_to = save_scheme_to
