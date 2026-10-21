"""Canvas main windows which save and open Ewoks workflow files (JSON/YAML)
next to Orange workflow files (.ows).

The existing File menu actions are reused: the main window methods behind them
are reimplemented.
"""

import io
import logging
import os
import tempfile
from pathlib import Path
from typing import IO
from typing import Optional
from typing import Union

from AnyQt.QtCore import QSettings
from AnyQt.QtCore import Qt
from AnyQt.QtWidgets import QFileDialog
from orangecanvas.application.canvasmain import CanvasMainWindow
from orangecanvas.application.canvasmain import user_documents_path
from orangecanvas.gui.utils import message_critical
from orangecanvas.scheme import Scheme

from ...orange_version import ORANGE_VERSION
from ..workflows.owscheme import ewoks_to_ows
from ..workflows.owscheme import ows_to_ewoks

if ORANGE_VERSION == ORANGE_VERSION.latest_orange:
    from Orange.canvas.mainwindow import MainWindow as _BaseMainWindow
else:
    # Note: OASYS2's `OASYSMainWindow` is handled in `oasys_mainwindow`
    _BaseMainWindow = CanvasMainWindow

_logger = logging.getLogger(__name__)

EWOKS_FILE_SUFFIXES = (".json", ".yml", ".yaml")
EWOKS_FILE_FILTER = "Ewoks workflow (*.json *.yml *.yaml)"
_OWS_FILE_FILTER = "Orange Workflow (*.ows)"


def is_ewoks_workflow_file(filename: Union[str, Path, None]) -> bool:
    return bool(filename) and Path(filename).suffix.lower() in EWOKS_FILE_SUFFIXES


def ewoks_to_ows_stream(filename: str) -> io.BytesIO:
    buffer = io.BytesIO()
    ewoks_to_ows(filename, buffer, error_on_duplicates=False)
    buffer.seek(0)
    return buffer


class EwoksCanvasMainWindowMixin:
    """Save and open Ewoks workflow files next to Orange workflow files.

    The Ewoks workflow file stays the document path, so saving keeps the Ewoks format.
    """

    def _open_workflow_dialog(self) -> QFileDialog:
        # Used by "Open", "Open and Freeze" and the welcome dialog
        dialog = super()._open_workflow_dialog()
        dialog.setNameFilters([*dialog.nameFilters(), EWOKS_FILE_FILTER])
        return dialog

    def check_requires(self, fileobj: IO) -> bool:
        filename = getattr(fileobj, "name", None)
        if is_ewoks_workflow_file(filename):
            fileobj = ewoks_to_ows_stream(filename)
        return super().check_requires(fileobj)

    def new_scheme_from_contents_and_path(
        self, fileobj: IO, path: str
    ) -> Optional[Scheme]:
        if is_ewoks_workflow_file(path):
            try:
                fileobj = ewoks_to_ows_stream(path)
            except Exception:
                _logger.exception("")
                message_critical(
                    self.tr("Could not load an Ewoks workflow file."),
                    title=self.tr("Error"),
                    informative_text=self.tr(
                        "An unexpected error occurred while loading '%s'."
                    )
                    % path,
                    exc_info=True,
                    parent=self,
                )
                return None
        return super().new_scheme_from_contents_and_path(fileobj, path)

    def save_scheme_to(self, scheme: Scheme, filename: str) -> bool:
        if not is_ewoks_workflow_file(filename):
            return super().save_scheme_to(scheme, filename)

        # --- BEGIN copy of `orangecanvas` `CanvasMainWindow.save_scheme_to` (orange-canvas-core 0.2.8) ---
        # Ewoks changes are marked `Ewoks:`. Compare with upstream when updating orange-canvas-core.
        dirname, basename = os.path.split(filename)
        try:
            scheme.set_runtime_env("basedir", os.path.abspath(dirname))
            buffer = io.BytesIO()
            scheme.save_to(buffer, pretty=True, pickle_fallback=True)
            # Ewoks: convert the .ows content to an Ewoks graph and dump it in the
            # format given by the file suffix
            buffer.seek(0)
            graph = ows_to_ewoks(buffer)
            # Do not truncate an existing file when the serialization fails
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpname = os.path.join(tmpdir, basename)
                graph.dump(tmpname)
                with open(tmpname, "rb") as f:
                    content = f.read()
            with open(filename, "wb") as f:
                f.write(content)
        except Exception:
            _logger.error("Error saving %r to %r", scheme, filename, exc_info=True)
            message_critical(
                self.tr('An error occurred while trying to save workflow "%s" to "%s"')
                % (scheme.title or self.tr("untitled"), basename),
                title=self.tr("Error saving %s") % basename,
                exc_info=True,
                parent=self,
            )
            return False
        self.clear_swp()
        return True
        # --- END copy of `orangecanvas` `CanvasMainWindow.save_scheme_to` ---

    def save_scheme_as(self) -> int:
        """Reimplemented to let the user choose the Ewoks workflow format."""
        # --- BEGIN copy of `orangecanvas` `CanvasMainWindow.save_scheme_as` (orange-canvas-core 0.2.8) ---
        # Ewoks changes are marked `Ewoks:`. Compare with upstream when updating orange-canvas-core.
        document = self.current_document()
        curr_scheme = document.scheme()
        if curr_scheme is None:
            return QFileDialog.Rejected
        settings = QSettings()
        settings.beginGroup("mainwindow")

        path = document.path()
        if path:
            start_path = path
        else:
            start_dir = settings.value("last-scheme-dir", "", type=str)
            if not os.path.isdir(start_dir):
                start_dir = user_documents_path()
            title = curr_scheme.title or self.tr("untitled")
            start_path = os.path.join(start_dir, title + ".ows")

        dialog = QFileDialog(
            self,
            windowTitle=self.tr("Save Workflow File"),
            directory=start_path,
            fileMode=QFileDialog.AnyFile,
            acceptMode=QFileDialog.AcceptSave,
            windowModality=Qt.WindowModal,
            objectName="save-as-ows-filedialog",
        )
        # Ewoks: add the Ewoks file filter and match the default suffix to the
        # selected filter
        dialog.setNameFilters([_OWS_FILE_FILTER, EWOKS_FILE_FILTER])

        def set_default_suffix(name_filter: str) -> None:
            if name_filter == EWOKS_FILE_FILTER:
                dialog.setDefaultSuffix("json")
            else:
                dialog.setDefaultSuffix("ows")

        if is_ewoks_workflow_file(path):
            dialog.selectNameFilter(EWOKS_FILE_FILTER)
        set_default_suffix(dialog.selectedNameFilter())
        dialog.filterSelected.connect(set_default_suffix)
        # Ewoks: end of the Ewoks file filter handling
        # As `CanvasMainWindow.save_scheme_as`: deleted after `exec`
        dialog.deleteLater()

        if not dialog.exec():
            return QFileDialog.Rejected
        filename = dialog.selectedFiles()[0]
        settings.setValue("last-scheme-dir", os.path.dirname(filename))
        if not self.save_scheme_to(curr_scheme, filename):
            return QFileDialog.Rejected
        document.setPath(filename)
        document.setModified(False)
        self.add_recent_scheme(curr_scheme.title, document.path())
        return QFileDialog.Accepted
        # --- END copy of `orangecanvas` `CanvasMainWindow.save_scheme_as` ---


class EwoksCanvasMainWindow(EwoksCanvasMainWindowMixin, _BaseMainWindow):
    """Main window of the Ewoks canvas (Orange3 or orange-canvas-core)."""
