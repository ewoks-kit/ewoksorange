from AnyQt import QtWidgets
from AnyQt.QtCore import Qt
import numbers
from ewokscore.hashing import UniversalHashable


class ParameterForm(QtWidgets.QWidget):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent=parent)
        self.initUI(**kwargs)
        self._fields = dict()

    def initUIParent(self):
        parent = self.parent()
        if parent is None:
            return
        layout = parent.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout()
            parent.setLayout(layout)
        layout.addWidget(self)

    def initUI(self, margin=0, spacing=4):
        self.initUIParent()
        layout = QtWidgets.QFormLayout()
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(spacing)
        policy = QtWidgets.QFormLayout.AllNonFixedFieldsGrow
        layout.setFieldGrowthPolicy(policy)
        # layout.setFormAlignment(Qt.AlignHCenter | Qt.AlignTop)
        layout.setLabelAlignment(Qt.AlignLeft)
        self.setLayout(layout)

    # def sizeHint(self):
    #    s = super().sizeHint()
    #    return QtCore.QSize(int(1.5 * s.width()), s.height())

    def addParameter(self, name, value=None, default="", changeCallback=None):
        label = name + ":"
        if value is None or value is UniversalHashable.MISSING_DATA:
            value = default
        if isinstance(value, str):
            field = QtWidgets.QLineEdit()
            field.setText(value)
            if changeCallback:
                field.textChanged.connect(changeCallback)
            else:
                field.setReadOnly(True)
        elif isinstance(value, numbers.Number):
            if isinstance(value, numbers.Integral):
                field = QtWidgets.QSpinBox()
                field.setRange(-(2 ** 31), 2 ** 31 - 1)
            else:
                field = QtWidgets.QDoubleSpinBox()
            field.setValue(value)
            if changeCallback:
                field.editingFinished.connect(changeCallback)
            else:
                field.setReadOnly(True)
        else:
            raise ValueError(
                "{} does not have a Qt widget".format(repr(type(value).__qualname__))
            )
        # Append
        policy = QtWidgets.QSizePolicy.Expanding
        field.setSizePolicy(policy, policy)
        self.layout().addRow(label, field)
        self._fields[name] = field

    def getParameter(self, name):
        field = self._fields[name]
        if isinstance(field, QtWidgets.QLineEdit):
            return field.text()
        else:
            return field.value()

    def setParameter(self, name, value):
        field = self._fields[name]
        if isinstance(field, QtWidgets.QLineEdit):
            field.setText(str(value))
        else:
            field.setValue(value)

    def enable(self, name):
        if name in self._fields:
            field = self._fields[name]
            field.setEnabled(True)

    def disable(self, name):
        if name in self._fields:
            field = self._fields[name]
            field.setEnabled(False)

    def getParameters(self):
        return {name: self.getParameter(name) for name in self._fields}
