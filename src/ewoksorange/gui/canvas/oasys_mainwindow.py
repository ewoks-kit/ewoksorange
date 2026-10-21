"""OASYS2 version of `mainwindow.EwoksCanvasMainWindow`.

Must be imported after `oasys2.canvas.config.OasysConfig` is patched (see `main`).
"""

import os
import tempfile
from pathlib import Path

from AnyQt.QtCore import QSettings
from AnyQt.QtCore import QStandardPaths
from AnyQt.QtWidgets import QDialog
from AnyQt.QtWidgets import QFileDialog
from oasys2.canvas.application.canvasmain import OASYSMainWindow
from orangecanvas.gui.utils import message_critical

from ..workflows.owscheme import ewoks_to_ows
from .mainwindow import EWOKS_FILE_FILTER
from .mainwindow import EwoksCanvasMainWindowMixin
from .mainwindow import is_ewoks_workflow_file


class EwoksOasysMainWindow(EwoksCanvasMainWindowMixin, OASYSMainWindow):
    """OASYS2 opens workflows with its own (private) methods instead of
    `CanvasMainWindow.open_scheme` and `CanvasMainWindow.load_scheme`.
    """

    def _open_scheme(self):
        """Reimplemented to add the Ewoks workflow file filter."""
        document = self.current_document()
        if document.isModifiedStrict():
            if self.ask_save_changes() == QDialog.Rejected:
                return QDialog.Rejected

        start_directory = self.last_scheme_directory
        if start_directory is None:
            start_directory = QSettings().value(
                "output/default-working-directory",
                QStandardPaths.standardLocations(
                    QStandardPaths.StandardLocation.DocumentsLocation
                )[0],
                type=str,
            )

        filename, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Open OASYS Workflow File"),
            start_directory,
            ";;".join([self.tr("OASYS Workflow (*.ows)"), EWOKS_FILE_FILTER]),
        )
        if not filename:
            return QDialog.Rejected
        return self._load_scheme(filename)

    def _new_scheme_from(self, filename):
        """Reimplemented to load Ewoks workflow files."""
        if not is_ewoks_workflow_file(filename):
            return super()._new_scheme_from(filename)
        # OASYS2 only loads from a path. The working directory of an OASYS2
        # workflow does not depend on that path.
        with tempfile.TemporaryDirectory() as tmpdir:
            ows_filename = os.path.join(tmpdir, Path(filename).stem + ".ows")
            try:
                ewoks_to_ows(filename, ows_filename, error_on_duplicates=False)
            except Exception:
                message_critical(
                    self.tr("Could not load an Ewoks workflow file."),
                    title=self.tr("Error"),
                    informative_text=self.tr(
                        "An unexpected error occurred while loading '%s'."
                    )
                    % filename,
                    exc_info=True,
                    parent=self,
                )
                return None
            return super()._new_scheme_from(ows_filename)
