from AnyQt import QtWidgets

from ewoksorange.gui.owwidgets.nothread import OWEwoksWidgetNoThread
from ewoksorange.gui.utils import invalid_data
from ewoksorange.tasks import SaveWorkflow

__all__ = ["OWSaveWorkflow"]


class OWSaveWorkflow(OWEwoksWidgetNoThread, ewokstaskclass=SaveWorkflow):
    name = "Save workflow"
    description = "Save the current workflow and its settings to an .ows file"
    icon = "icons/save.svg"
    want_main_area = False

    def __init__(self):
        super().__init__()
        self._init_control_area()

    def _init_control_area(self) -> None:
        layout = self._get_control_layout()

        file_layout = QtWidgets.QHBoxLayout()
        self._filename_edit = QtWidgets.QLineEdit()
        self._filename_edit.setPlaceholderText("workflow.ows")
        self._filename_edit.setText(self.get_default_input_value("filename", ""))
        self._filename_edit.editingFinished.connect(self._filename_changed)
        file_layout.addWidget(self._filename_edit)
        browse = QtWidgets.QPushButton("Browse...")
        browse.released.connect(self._browse)
        file_layout.addWidget(browse)
        layout.addLayout(file_layout)

        save = QtWidgets.QPushButton("Save")
        save.released.connect(self.execute_ewoks_task)
        layout.addWidget(save)

    def _browse(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save workflow",
            self._filename_edit.text(),
            "Orange Workflow (*.ows)",
        )
        if not filename:
            return
        if not filename.endswith(".ows"):
            filename += ".ows"
        self._filename_edit.setText(filename)
        self._filename_changed()

    def _filename_changed(self) -> None:
        filename = self._filename_edit.text().strip()
        if filename:
            self.set_default_input("filename", filename)
        else:
            self.set_default_input("filename", invalid_data.INVALIDATION_DATA)
