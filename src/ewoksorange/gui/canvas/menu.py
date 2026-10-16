import io
import logging
import os
import tempfile
from pathlib import Path

from AnyQt.QtCore import QUrl
from AnyQt.QtWidgets import QDialog
from AnyQt.QtWidgets import QFileDialog
from orangecanvas.application import canvasmain
from orangecanvas.application.canvasmain import CanvasMainWindow

from ...orange_version import ORANGE_VERSION
from ..workflows.owscheme import ewoks_to_ows
from ..workflows.owscheme import ows_to_ewoks

_logger = logging.getLogger(__name__)
_SUFFIXES = (".json", ".yml", ".yaml")
_FILTER = "Ewoks workflow (*.json *.yml *.yaml)"
_patched = False


def _is_ewoks_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in _SUFFIXES


def _import_ewoks_workflow(window: CanvasMainWindow, filename: str) -> None:
    from ...bindings import load_graph  # Lazy import to avoid circular import

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


def _export_ewoks_workflow(window: CanvasMainWindow, filename: str) -> None:
    from ...bindings import save_graph  # Lazy import to avoid circular import

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


class _EwoksSaveDialog(QFileDialog):
    """Save As dialog with an extra Ewoks filter.

    Choosing an Ewoks file exports the workflow and rejects the dialog, so that
    the document path and modified state (and thus Ctrl+S) keep targeting `.ows`.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._window = args[0] if args else kwargs.get("parent")

    def setNameFilter(self, name_filter):
        self.setNameFilters([name_filter, _FILTER])

    def exec(self):
        accepted = super().exec()
        if not accepted:
            return accepted
        filename = self.selectedFiles()[0]
        if not _is_ewoks_file(filename):
            return accepted
        _export_ewoks_workflow(self._window, filename)
        # Reject so any further saving is skipped
        return 0

    exec_ = exec


def _patch_open_save() -> None:
    original_open_dialog = CanvasMainWindow._open_workflow_dialog
    original_open_file = CanvasMainWindow.open_scheme_file
    original_save_as = CanvasMainWindow.save_scheme_as

    def _open_workflow_dialog(self):
        dialog = original_open_dialog(self)
        dialog.setNameFilters([*dialog.nameFilters(), _FILTER])
        return dialog

    def open_scheme_file(self, filename, **kwargs):
        path = filename.toLocalFile() if isinstance(filename, QUrl) else filename
        if _is_ewoks_file(path):
            _import_ewoks_workflow(self, path)
        else:
            original_open_file(self, filename, **kwargs)

    def save_scheme_as(self):
        original = canvasmain.QFileDialog
        canvasmain.QFileDialog = _EwoksSaveDialog
        try:
            return original_save_as(self)
        finally:
            canvasmain.QFileDialog = original

    CanvasMainWindow._open_workflow_dialog = _open_workflow_dialog
    CanvasMainWindow.open_scheme_file = open_scheme_file
    CanvasMainWindow.save_scheme_as = save_scheme_as


def _patch_oasys_open() -> None:
    """OASYS2 has its own Open dialog (a static ``QFileDialog.getOpenFileName``)."""
    # Imported late: it must come after the OasysConfig patch of `canvas.main`.
    from oasys2.canvas.application import canvasmain as oasys_canvasmain

    window_class = oasys_canvasmain.OASYSMainWindow
    original_open = window_class._open_scheme
    original_load = window_class._load_scheme

    class _OasysOpenDialog(QFileDialog):
        @staticmethod
        def getOpenFileName(parent=None, caption="", directory="", filter="", *args):
            return QFileDialog.getOpenFileName(
                parent, caption, directory, f"{filter};;{_FILTER}", *args
            )

    def _open_scheme(self):
        original = oasys_canvasmain.QFileDialog
        oasys_canvasmain.QFileDialog = _OasysOpenDialog
        try:
            return original_open(self)
        finally:
            oasys_canvasmain.QFileDialog = original

    def _load_scheme(self, filename):
        if _is_ewoks_file(str(filename)):
            _import_ewoks_workflow(self, str(filename))
            return QDialog.Accepted
        return original_load(self, filename)

    window_class._open_scheme = _open_scheme
    window_class._load_scheme = _load_scheme


def add_ewoks_file_filters() -> None:
    """
    Add the Ewoks workflow filter to the Open and Save As dialogs of the canvas.
    """
    global _patched
    if _patched:
        return
    _patched = True
    _patch_open_save()
    if ORANGE_VERSION == ORANGE_VERSION.latest_oasys:
        _patch_oasys_open()
