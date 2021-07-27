from Orange.widgets.widget import OWWidget
import ewoksorange.tests.listoperations
from AnyQt.QtWidgets import QWidget, QPushButton, QFormLayout, QSpinBox
from Orange.widgets import gui
from Orange.widgets.widget import Output
import logging

_logger = logging.getLogger(__name__)


class ListGenerator(OWWidget):
    name = "ListGenerator"

    description = "Generate a random list with X elements"

    id = "orangecontrib.list_operations.listgenerator.ListGenerator"
    category = "esrfWidgets"
    ewokstaskclass = ewoksorange.tests.listoperations.GenerateList

    want_main_area = True

    class Outputs:
        list_ = Output("list", list)

    class ListLength(QWidget):
        def __init__(self, *args, **kwargs):
            QWidget.__init__(self, *args, **kwargs)
            self.setLayout(QFormLayout())
            self._lengthQSB = QSpinBox(self)
            self.layout().addRow("length", self._lengthQSB)
            self._lengthQSB.setMaximum(10000000)
            self._lengthQSB.setSingleStep(1000)
            self._lengthQSB.setValue(100000)

        def getLength(self):
            return self._lengthQSB.value()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._widget = self.ListLength(parent=self)

        self._box = gui.vBox(self.mainArea, self.name)
        layout = self._box.layout()
        layout.addWidget(self._widget)

        self._validateButton = QPushButton("generate", self)
        layout.addWidget(self._validateButton)

        # connect signal / slot
        self._validateButton.released.connect(self._validate)

    def getList(self):
        task = ewoksorange.tests.listoperations.GenerateList(
            inputs={"length": self._widget.getLength()}
        )
        task.run()
        return task.outputs.iterable

    def _validate(self):
        self.Outputs.list_.send(self.getList())
