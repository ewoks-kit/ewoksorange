from AnyQt.QtWidgets import QPushButton
from Orange.widgets import gui
from ewoksorange.bindings import OWEwoksWidgetNoThread
from ewoksorange.gui.parameterform import ParameterForm
from ewoksorange.tests.listoperations import GenerateList


class ListGenerator(OWEwoksWidgetNoThread, ewokstaskclass=GenerateList):
    name = "List generator"
    description = "Generate a random list with X elements"
    icon = "icons/mywidget.svg"
    want_main_area = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        box = gui.widgetBox(self.controlArea, "Static Inputs")
        self._static_input_form = ParameterForm(parent=box)
        for name, value in self.static_input_values.items():
            self._static_input_form.addParameter(
                name, value=value, default=0, changeCallback=self.staticInputHasChanged
            )

        box = gui.widgetBox(self.controlArea, "Dynamic Inputs")
        self._dynamic_input_form = ParameterForm(parent=box)
        for name in self.input_names():
            self._dynamic_input_form.addParameter(name)

        box = gui.widgetBox(self.controlArea, "Outputs")
        self._output_form = ParameterForm(parent=box)
        for name in self.output_names():
            self._output_form.addParameter(name)

        box = gui.widgetBox(self.controlArea, "Commands")
        layout = box.layout()
        self._validateButton = QPushButton("generate", self)
        layout.addWidget(self._validateButton)

        # connect signal / slot
        self._validateButton.released.connect(self.handleNewSignals)

    def staticInputHasChanged(self):
        self.static_input.update(self._static_input_form.getParameters())
        super().staticInputHasChanged()

    def handleNewSignals(self):
        for name, value in self.dynamic_input_values.items():
            self._dynamic_input_form.setParameter(name, value)
            self._static_input_form.disable(name)
        super().handleNewSignals()
        for name, value in self.output_values.items():
            self._output_form.setParameter(name, value)
