import os
import logging
import numbers
from typing import Any, Callable, Dict, List, Sequence, Set, Union, Optional
from contextlib import contextmanager

from AnyQt import QtCore
from AnyQt import QtWidgets
from silx.gui.dialog.DataFileDialog import DataFileDialog
from ewokscore import missing_data

_logger = logging.getLogger(__name__)

ParameterValueType = Any
WidgetValueType = Union[str, numbers.Number, bool, missing_data.MissingData]


def default_serialize(value: ParameterValueType) -> WidgetValueType:
    return value


def default_deserialize(value: WidgetValueType) -> ParameterValueType:
    return value


@contextmanager
def block_signals(w: QtWidgets.QWidget):
    old = w.blockSignals(True)
    try:
        yield
    finally:
        w.blockSignals(old)


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
        value: ParameterValueType = missing_data.MISSING_DATA,
        value_for_type: Any = "",
        value_change_callback: Optional[Callable] = None,
        label: Optional[str] = None,
        readonly: Optional[bool] = None,
        enabled: Optional[bool] = None,
        select: Optional[str] = None,
        select_label: str = "...",
        checked: Optional[bool] = None,
        checkbox_label: str = "checked",
        serialize: Callable[[ParameterValueType], WidgetValueType] = default_serialize,
        deserialize: Callable[
            [WidgetValueType], ParameterValueType
        ] = default_deserialize,
        bool_label: str = "",
    ):
        """Each row has the following widgets:

        - label widget: name of the parameter by default
        - value widget: MISSING_DATA by default
        - select button (optional): select file/directory/HDF5 url
        - check box (optional): checked by default

        Parameters have folowing properties:

        - readonly: the means you can edit the value
                    Default: False when value_change_callback is provided, True otherwise
        - enabled: when False all widgets are disabled (grey color)
                   Default: True
        - checked: can mean whatever the user wants
        """
        if not label:
            label = name

        has_callback = bool(value_change_callback)
        if readonly is None:
            readonly = not has_callback
        if enabled is None:
            enabled = True

        _logger.debug(
            "Parameter form: initialize parameter %r (readonly = %s, enabled = %s, type = %s, missing = %s)",
            name,
            readonly,
            enabled,
            type(value_for_type),
            missing_data.is_missing_data(value),
        )

        label_widget = QtWidgets.QLabel(label)
        value_widget = None
        select_widget = None
        check_widget = None
        connections = list()

        if isinstance(value_for_type, str):
            value_widget = QtWidgets.QLineEdit()
            if value_change_callback:
                connections.append(
                    (value_widget.editingFinished.connect, value_change_callback)
                )
            if select == "file":
                select_widget = QtWidgets.QPushButton(select_label)
                connections.append(
                    (
                        select_widget.pressed.connect,
                        lambda: self._select_file(name, must_exist=True),
                    )
                )
            elif select == "newfile":
                select_widget = QtWidgets.QPushButton(select_label)
                connections.append(
                    (
                        select_widget.pressed.connect,
                        lambda: self._select_file(name, must_exist=False),
                    )
                )
            elif select == "directory":
                select_widget = QtWidgets.QPushButton(select_label)
                connections.append(
                    (
                        select_widget.pressed.connect,
                        lambda: self._select_directory(name),
                    )
                )
            elif select == "h5dataset":
                select_widget = QtWidgets.QPushButton(select_label)
                connections.append(
                    (
                        select_widget.pressed.connect,
                        lambda: self._select_h5dataset(name),
                    )
                )
            elif select == "h5group":
                select_widget = QtWidgets.QPushButton(select_label)
                connections.append(
                    (select_widget.pressed.connect, lambda: self._select_h5group(name))
                )
            elif select == "files":
                select_widget = QtWidgets.QPushButton(select_label)
                connections.append(
                    (
                        select_widget.pressed.connect,
                        lambda: self._select_file(name, must_exist=True, append=True),
                    )
                )
            elif select == "newfiles":
                select_widget = QtWidgets.QPushButton(select_label)
                connections.append(
                    (
                        select_widget.pressed.connect,
                        lambda: self._select_file(name, must_exist=False, append=True),
                    )
                )
            elif select == "directories":
                select_widget = QtWidgets.QPushButton(select_label)
                connections.append(
                    (
                        select_widget.pressed.connect,
                        lambda: self._select_directory(name, append=True),
                    )
                )
            elif select == "h5datasets":
                select_widget = QtWidgets.QPushButton(select_label)
                connections.append(
                    (
                        select_widget.pressed.connect,
                        lambda: self._select_h5dataset(name, append=True),
                    )
                )
            elif select == "h5groups":
                select_widget = QtWidgets.QPushButton(select_label)
                connections.append(
                    (
                        select_widget.pressed.connect,
                        lambda: self._select_h5group(name, append=True),
                    )
                )
            else:
                select_widget = None
        elif isinstance(value_for_type, bool):
            value_widget = QtWidgets.QCheckBox(bool_label)
            if value_change_callback:
                connections.append(
                    (value_widget.stateChanged.connect, value_change_callback)
                )
        elif isinstance(value_for_type, numbers.Number):
            if isinstance(value_for_type, numbers.Integral):
                value_widget = QtWidgets.QSpinBox()
                value_widget.setRange(-(2**31), 2**31 - 1)
            else:
                value_widget = QtWidgets.QDoubleSpinBox()
                value_widget.setRange(-(2**52), 2**52 - 1)
            if value_change_callback:
                connections.append(
                    (value_widget.editingFinished.connect, value_change_callback)
                )
        elif isinstance(value_for_type, Sequence):
            value_widget = QtWidgets.QComboBox()
            value_widget.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
            value_widget.addItem("<missing>", missing_data.MISSING_DATA)
            for data in value_for_type:
                value_widget.addItem(str(data), data)
            if value_change_callback:
                connections.append(
                    (value_widget.currentIndexChanged.connect, value_change_callback)
                )
        else:
            raise TypeError(
                f"Parameter '{name}' with type '{type(value)}' does not have a Qt widget"
            )

        if checked is not None:
            check_widget = QtWidgets.QCheckBox(checkbox_label)
            check_widget.setChecked(checked)
            if value_change_callback:
                connections.append(
                    (check_widget.stateChanged.connect, value_change_callback)
                )

        policy = QtWidgets.QSizePolicy.Expanding
        value_widget.setSizePolicy(policy, policy)
        grid = self.layout()
        row = grid.rowCount()
        grid.addWidget(label_widget, row, 0)
        if value_widget:
            grid.addWidget(value_widget, row, 1)
        if select_widget:
            grid.addWidget(select_widget, row, 2)
        if check_widget:
            grid.addWidget(check_widget, row, 3)

        self._fields[name] = {
            "row": row,
            "deserialize": deserialize,
            "serialize": serialize,
        }

        self.set_parameter_value(name, value)
        self.set_parameter_readonly(name, readonly)
        self.set_parameter_enabled(name, enabled)
        for connect, func in connections:
            connect(func)

    def _get_widget(self, name: str, col: int) -> QtWidgets.QWidget:
        if name not in self._fields:
            return None
        row = self._fields[name]["row"]
        item = self.layout().itemAtPosition(row, col)
        if item is None:
            return None
        return item.widget()

    def _get_label_widget(self, name: str) -> QtWidgets.QWidget:
        return self._get_widget(name, 0)

    def _get_value_widget(self, name: str) -> QtWidgets.QWidget:
        return self._get_widget(name, 1)

    def _get_select_widget(self, name: str) -> QtWidgets.QWidget:
        return self._get_widget(name, 2)

    def _get_check_widget(self, name: str) -> QtWidgets.QWidget:
        return self._get_widget(name, 3)

    def has_parameter(self, name: str):
        w = self._get_value_widget(name)
        return w is not None

    def get_parameter_value(self, name: str):
        w = self._get_value_widget(name)
        if w is None:
            return missing_data.MISSING_DATA

        if isinstance(w, QtWidgets.QLineEdit):
            wvalue = w.text()
        elif isinstance(w, QtWidgets.QCheckBox):
            wvalue = w.isChecked()
        elif isinstance(w, QtWidgets.QComboBox):
            wvalue = w.currentData()
            # TODO: check what it returns when index is -1
        else:
            wvalue = w.value()

        fdict = self._fields[name]
        changed = wvalue != fdict["last_widget_value"]
        if changed:
            fdict["last_widget_value"] = wvalue
        elif fdict["null"]:
            return missing_data.MISSING_DATA

        deserialize = fdict["deserialize"]
        try:
            value = deserialize(wvalue)
        except Exception:
            value = missing_data.MISSING_DATA
            fdict["null"] = True
        else:
            fdict["null"] = missing_data.is_missing_data(value)

        return value

    def set_parameter_value(self, name: str, value: ParameterValueType):
        """When the value cannot be serialized or cannot be set to the widget,
        the parameter value will set to MISSING_DATA.
        """
        w = self._get_value_widget(name)
        if w is None:
            return

        fdict = self._fields[name]
        serialize = fdict["serialize"]
        if missing_data.is_missing_data(value):
            set_value = missing_data.MISSING_DATA
        else:
            try:
                set_value = serialize(value)
            except Exception:
                set_value = missing_data.MISSING_DATA

        if isinstance(w, QtWidgets.QLineEdit):
            _logger.debug("Parameter form: set string parameter %r = %r", name, value)
            try:
                with block_signals(w):
                    w.setText(set_value)
            except TypeError:
                with block_signals(w):
                    w.setText("")
                fdict["null"] = True
                fdict["last_widget_value"] = ""
            else:
                fdict["null"] = False
                fdict["last_widget_value"] = set_value
        elif isinstance(w, QtWidgets.QCheckBox):
            _logger.debug("Parameter form: set boolean parameter %r = %r", name, value)
            try:
                with block_signals(w):
                    w.setChecked(set_value)
            except TypeError:
                with block_signals(w):
                    w.setChecked(False)
                fdict["null"] = True
                fdict["last_widget_value"] = False
            else:
                fdict["null"] = False
                fdict["last_widget_value"] = set_value
        elif isinstance(w, QtWidgets.QComboBox):
            _logger.debug(
                "Parameter form: select choice parameter %r = %r", name, value
            )
            idx = w.findData(set_value)
            if idx == -1:
                with block_signals(w):
                    w.setCurrentIndex(0)
                fdict["null"] = True
                fdict["last_widget_value"] = missing_data.MISSING_DATA
            else:
                with block_signals(w):
                    w.setCurrentIndex(idx)
                fdict["null"] = False
                fdict["last_widget_value"] = set_value
        else:
            _logger.debug(
                "Parameter form: set numerical parameter %r = %r", name, value
            )
            try:
                with block_signals(w):
                    w.setValue(set_value)
            except TypeError:
                with block_signals(w):
                    w.setValue(0)
                fdict["null"] = True
                fdict["last_widget_value"] = 0
            else:
                fdict["null"] = False
                fdict["last_widget_value"] = set_value

    def get_parameter_readonly(self, name: str) -> Optional[bool]:
        w = self._get_value_widget(name)
        if w is not None:
            if isinstance(w, QtWidgets.QCheckBox):
                return w.isEnabled()
            elif isinstance(w, QtWidgets.QComboBox):
                return w.isEnabled()
            else:
                return w.isReadOnly()

    def set_parameter_readonly(self, name: str, value: bool) -> None:
        w = self._get_value_widget(name)
        if w is not None:
            if isinstance(w, QtWidgets.QCheckBox):
                return w.setEnabled(value)
            elif isinstance(w, QtWidgets.QComboBox):
                return w.setEnabled(value)
            else:
                return w.setReadOnly(value)

    def get_parameter_enabled(self, name: str) -> Optional[bool]:
        w = self._get_value_widget(name)
        if w is not None:
            return w.isEnabled()

    def set_parameter_enabled(self, name: str, value: bool) -> None:
        w = self._get_value_widget(name)
        if w is not None:
            w.setEnabled(value)

    def get_parameter_checked(self, name: str) -> Optional[bool]:
        w = self._get_check_widget(name)
        if w is not None:
            return w.isChecked()

    def set_parameter_checked(self, name: str, value: bool) -> None:
        w = self._get_check_widget(name)
        if w is not None:
            w.setChecked(value)

    def get_parameter_names(self) -> Set[str]:
        return set(self._fields)

    def get_parameter_values(self) -> Dict[str, ParameterValueType]:
        return {name: self.get_parameter_value(name) for name in self._fields}

    def set_parameter_values(self, params: Dict[str, ParameterValueType]) -> None:
        for name, value in params.items():
            self.set_parameter_value(name, value)

    def get_parameters_readonly(self) -> Dict[str, bool]:
        return {name: self.get_parameter_readonly(name) for name in self._fields}

    def set_parameters_readonly(self, params: Dict[str, bool]) -> None:
        for name, value in params.items():
            self.set_parameter_readonly(name, value)

    def get_parameters_checked(self) -> Dict[str, bool]:
        result = dict()
        for name in self._fields:
            checked = self.get_parameter_checked(name)
            if checked is None:
                continue
            result[name] = checked
        return result

    def set_parameters_checked(self, params: Dict[str, bool]) -> None:
        for name, value in params.items():
            self.set_parameter_checked(name, value)

    def get_parameters_enabled(self) -> Dict[str, bool]:
        return {name: self.get_parameter_enabled(name) for name in self._fields}

    def set_parameters_enabled(self, params: Dict[str, bool]) -> None:
        for name, value in params.items():
            self.set_parameter_enabled(name, value)

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
        if value:
            value = value.replace("?/", "?path=/")
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
        if value:
            value = value.replace("?/", "?path=/")
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

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Enter or key == QtCore.Qt.Key_Return:
            # TODO: Orange3 causes a button in focus to be pressed due to this event.
            return
        super().keyPressEvent(event)
