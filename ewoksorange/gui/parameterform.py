import os
import numbers
from typing import Any, Callable, Dict, List, Union, Optional
from AnyQt import QtWidgets
from silx.gui.dialog.DataFileDialog import DataFileDialog
from ewoksorange.bindings import owwidgets


ParameterValueType = Any
WidgetValueType = Union[str, numbers.Number, bool]


def default_serialize(value: ParameterValueType) -> WidgetValueType:
    if value is owwidgets.INVALIDATION_DATA or value is owwidgets.MISSING_DATA:
        return ""
    else:
        return value


def default_deserialize(value: WidgetValueType) -> ParameterValueType:
    if isinstance(value, str) and not value:
        return owwidgets.MISSING_DATA
    else:
        return value


class ParameterForm(QtWidgets.QWidget):
    def __init__(self, *args, margin=0, spacing=4, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_ui(margin=margin, spacing=spacing)
        self._fields = dict()

    def _init_ui(self, margin=0, spacing=4):
        self._init_parent_ui()
        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(spacing)
        self.setLayout(layout)

    def _init_parent_ui(self):
        parent = self.parent()
        if parent is None:
            return
        layout = parent.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout()
            parent.setLayout(layout)
        layout.addWidget(self)

    def addParameter(
        self,
        name: str,
        value: ParameterValueType = owwidgets.MISSING_DATA,
        default: ParameterValueType = owwidgets.MISSING_DATA,
        label: Optional[str] = None,
        changeCallback: Optional[Callable] = None,
        select: Optional[str] = None,
        select_label: str = "...",
        onoff: Optional[bool] = None,
        onoff_label: str = "enabled",
        enable_when_on: bool = True,
        serialize: Callable[[ParameterValueType], WidgetValueType] = default_serialize,
        deserialize: Callable[
            [WidgetValueType], ParameterValueType
        ] = default_deserialize,
        bool_label: str = "",
    ):
        if label:
            label += ":"
        else:
            label = name + ":"
        if isinstance(value, type(owwidgets.MISSING_DATA)):
            value = default
        if value is owwidgets.INVALIDATION_DATA or value is owwidgets.MISSING_DATA:
            value = default
        try:
            value = serialize(value)
        except Exception as e:
            raise ValueError(f"Cannot serialize parameter '{name}'") from e

        label_widget = QtWidgets.QLabel(label)
        last_widget = None
        if isinstance(value, str):
            value_widget = QtWidgets.QLineEdit()
            value_widget.setText(value)
            if changeCallback:
                value_widget.textChanged.connect(changeCallback)
            else:
                value_widget.setReadOnly(True)
            if select == "file":
                last_widget = QtWidgets.QPushButton(select_label)
                last_widget.pressed.connect(
                    lambda: self._select_file(name, must_exist=True)
                )
            elif select == "newfile":
                last_widget = QtWidgets.QPushButton(select_label)
                last_widget.pressed.connect(
                    lambda: self._select_file(name, must_exist=False)
                )
            elif select == "directory":
                last_widget = QtWidgets.QPushButton(select_label)
                last_widget.pressed.connect(lambda: self._select_directory(name))
            elif select == "h5dataset":
                last_widget = QtWidgets.QPushButton(select_label)
                last_widget.pressed.connect(lambda: self._select_h5dataset(name))
            elif select == "h5group":
                last_widget = QtWidgets.QPushButton(select_label)
                last_widget.pressed.connect(lambda: self._select_h5group(name))
            elif select == "files":
                last_widget = QtWidgets.QPushButton(select_label)
                last_widget.pressed.connect(
                    lambda: self._select_file(name, must_exist=True, append=True)
                )
            elif select == "newfiles":
                last_widget = QtWidgets.QPushButton(select_label)
                last_widget.pressed.connect(
                    lambda: self._select_file(name, must_exist=False, append=True)
                )
            elif select == "directories":
                last_widget = QtWidgets.QPushButton(select_label)
                last_widget.pressed.connect(
                    lambda: self._select_directory(name, append=True)
                )
            elif select == "h5datasets":
                last_widget = QtWidgets.QPushButton(select_label)
                last_widget.pressed.connect(
                    lambda: self._select_h5dataset(name, append=True)
                )
            elif select == "h5groups":
                last_widget = QtWidgets.QPushButton(select_label)
                last_widget.pressed.connect(
                    lambda: self._select_h5dataset(name, append=True)
                )
            else:
                last_widget = None
        elif isinstance(value, bool):
            value_widget = QtWidgets.QCheckBox(bool_label)
            value_widget.setChecked(value)
            if changeCallback:
                value_widget.stateChanged.connect(changeCallback)
            else:
                value_widget.setReadOnly(True)
        elif isinstance(value, numbers.Number):
            if isinstance(value, numbers.Integral):
                value_widget = QtWidgets.QSpinBox()
                value_widget.setRange(-(2**31), 2**31 - 1)
            else:
                value_widget = QtWidgets.QDoubleSpinBox()
            value_widget.setValue(value)
            if changeCallback:
                value_widget.editingFinished.connect(changeCallback)
            else:
                value_widget.setReadOnly(True)
        else:
            raise TypeError(
                f"Parameter '{name}' with type '{type(value)}' does not have a Qt widget"
            )

        if onoff is not None:
            last_widget = QtWidgets.QCheckBox(onoff_label)
            last_widget.stateChanged.connect(
                lambda: self.set_parameter_enabled(
                    name, last_widget.isChecked() == enable_when_on
                )
            )
            if changeCallback:
                last_widget.stateChanged.connect(changeCallback)
            else:
                last_widget.setReadOnly(True)

        policy = QtWidgets.QSizePolicy.Expanding
        value_widget.setSizePolicy(policy, policy)
        grid = self.layout()
        row = grid.rowCount()
        grid.addWidget(label_widget, row, 0)
        if value_widget:
            grid.addWidget(value_widget, row, 1)
        if last_widget:
            grid.addWidget(last_widget, row, 2)

        self._fields[name] = {
            "row": row,
            "deserialize": deserialize,
            "serialize": serialize,
        }

        if onoff is not None:
            last_widget.setChecked(onoff)

    def _get_widget(self, name: str, col: int) -> QtWidgets.QWidget:
        if name not in self._fields:
            return None
        row = self._fields[name]["row"]
        return self.layout().itemAtPosition(row, col).widget()

    def _get_label_widget(self, name: str) -> QtWidgets.QWidget:
        return self._get_widget(name, 0)

    def _get_value_widget(self, name: str) -> QtWidgets.QWidget:
        return self._get_widget(name, 1)

    def has_parameter(self, name: str):
        w = self._get_value_widget(name)
        return w is not None

    def get_parameter_value(self, name: str):
        w = self._get_value_widget(name)
        if w is None:
            return
        if isinstance(w, QtWidgets.QLineEdit):
            value = w.text()
        else:
            value = w.value()
        deserialize = self._fields[name]["deserialize"]
        try:
            return deserialize(value)
        except Exception as e:
            raise ValueError(f"Cannot deserialize parameter '{name}'") from e

    def set_parameter_value(self, name: str, value: ParameterValueType):
        w = self._get_value_widget(name)
        if w is None:
            return
        try:
            value = self._fields[name]["serialize"](value)
        except Exception as e:
            raise ValueError(f"Cannot serialize parameter '{name}'") from e
        if isinstance(w, QtWidgets.QLineEdit):
            w.setText(str(value))
        elif isinstance(w, QtWidgets.QCheckBox):
            w.setChecked(value)
        else:
            w.setValue(value)

    def get_parameter_enabled(self, name: str) -> Optional[bool]:
        w = self._get_value_widget(name)
        if w is not None:
            return w.isEnabled()

    def set_parameter_enabled(self, name: str, value: bool) -> None:
        w = self._get_value_widget(name)
        if w is not None:
            w.setEnabled(value)

    def get_parameter_used(self, name: str) -> Optional[bool]:
        w = self._get_label_widget(name)
        if w is not None:
            return w.isEnabled()

    def set_parameter_used(self, name: str, value: bool) -> None:
        w = self._get_label_widget(name)
        if w is not None:
            w.setEnabled(value)

    def get_parameter_values(self) -> Dict[str, ParameterValueType]:
        return {name: self.get_parameter_value(name) for name in self._fields}

    def set_parameter_values(self, params: Dict[str, ParameterValueType]) -> None:
        for name, value in params.items():
            self.set_parameter_value(name, value)

    def get_parameters_enabled(self) -> Dict[str, bool]:
        return {name: self.get_parameter_enabled(name) for name in self._fields}

    def set_parameters_enabled(self, params: Dict[str, bool]) -> None:
        for name, value in params.items():
            self.set_parameter_enabled(name, value)

    def get_parameters_used(self) -> Dict[str, bool]:
        return {name: self.get_parameter_used(name) for name in self._fields}

    def set_parameters_used(self, params: Dict[str, bool]) -> None:
        for name, value in params.items():
            self.set_parameter_used(name, value)

    def _select_file(
        self, name: str, must_exist: bool = True, append: bool = False
    ) -> None:
        if append:
            filename = self._list_value_first(name)
        else:
            filename = self.get_parameter_value(name)
        dialog = QtWidgets.QFileDialog(self)
        if must_exist:
            dialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        else:
            dialog.setFileMode(QtWidgets.QFileDialog.AnyFile)
        if filename:
            dialog.setDirectory(os.path.dirname(filename))

        if not dialog.exec_():
            dialog.close()
            return

        value = dialog.selectedFiles()[0]
        if append:
            value = self._list_value_append(name, value)
        self.set_parameter_value(name, value)

    def _select_h5dataset(self, name: str, append: bool = False) -> None:
        if append:
            url = self._list_value_first(name)
        else:
            url = self.get_parameter_value(name)
        dialog = DataFileDialog(self)
        dialog.setFilterMode(DataFileDialog.FilterMode.ExistingDataset)
        if url:
            dialog.selectUrl(url)

        if not dialog.exec():
            dialog.close()
            return

        value = dialog.selectedUrl()
        if append:
            value = self._list_value_append(name, value)
        self.set_parameter_value(name, value)

    def _select_h5group(self, name: str, append: bool = False) -> None:
        if append:
            url = self._list_value_first(name)
        else:
            url = self.get_parameter_value(name)
        dialog = DataFileDialog(self)
        dialog.setFilterMode(DataFileDialog.FilterMode.ExistingGroup)
        if url:
            dialog.selectUrl(url)

        if not dialog.exec():
            dialog.close()
            return

        value = dialog.selectedUrl()
        if append:
            value = self._list_value_append(name, value)
        self.set_parameter_value(name, value)

    def _select_directory(self, name: str, append: bool = False) -> None:
        if append:
            directory = self._list_value_first(name)
        else:
            directory = self.get_parameter_value(name)
        dialog = QtWidgets.QFileDialog(self)
        dialog.setFileMode(QtWidgets.QFileDialog.DirectoryOnly)
        if directory:
            dialog.setDirectory(directory)

        if not dialog.exec_():
            dialog.close()
            return

        value = dialog.selectedFiles()[0]
        if append:
            value = self._list_value_append(name, value)
        self.set_parameter_value(name, value)

    def _list_value_append(self, name: str, value: str) -> List[str]:
        lst = self.get_parameter_value(name)
        if not lst:
            lst = [value]
        elif isinstance(lst, str):
            lst = [lst, value]
        elif isinstance(lst, list):
            lst.append(value)
        else:
            raise TypeError(value)
        return lst

    def _list_value_first(self, name: str) -> Optional[str]:
        lst = self.get_parameter_value(name)
        if not lst:
            return None
        elif isinstance(lst, str):
            return lst
        elif isinstance(lst, list):
            return lst[-1]
        else:
            raise TypeError(lst)
