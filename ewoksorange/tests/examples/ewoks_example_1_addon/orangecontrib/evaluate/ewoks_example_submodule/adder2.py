from Orange.widgets import gui
from Orange.widgets.widget import Input, Output

from ewoksorange.bindings import OWEwoksWidgetNoThread
from ewoksorange.gui.parameterform import ParameterForm
from ewokscore.tests.examples.tasks.sumtask import SumTask


__all__ = ["Adder2"]


class Adder2(OWEwoksWidgetNoThread, ewokstaskclass=SumTask):
    name = "Adder2"
    description = "Adds two numbers"
    icon = "icons/mywidget.svg"
    want_main_area = False

    class Inputs:
        a = Input("A", object)
        b = Input("B", object)

    class Outputs:
        result = Output("A + B", object)

    def __init__(self):
        super().__init__()

        box = gui.widgetBox(self.controlArea, "Default Inputs")
        self._default_inputs_form = ParameterForm(parent=box)
        for name, value in self.default_input_values.items():
            self._default_inputs_form.addParameter(
                name,
                value=value,
                default=0,
                changeCallback=self.defaultInputsHaveChanged,
            )

        box = gui.widgetBox(self.controlArea, "Dynamic Inputs")
        self._dynamic_input_form = ParameterForm(parent=box)
        for name in self.input_names():
            self._dynamic_input_form.addParameter(name)

        box = gui.widgetBox(self.controlArea, "Outputs")
        self._output_form = ParameterForm(parent=box)
        for name in self.output_names():
            self._output_form.addParameter(name)

        self.handleNewSignals()

    def defaultInputsHaveChanged(self):
        self.default_inputs.update(self._default_inputs_form.getParameters())
        super().defaultInputsHaveChanged()
        for name, value in self.output_values.items():
            self._output_form.setParameter(name, value)

    def handleNewSignals(self):
        for name, value in self.dynamic_input_values.items():
            self._dynamic_input_form.setParameter(name, value)
            self._default_inputs_form.disable(name)
        super().handleNewSignals()
        for name, value in self.output_values.items():
            self._output_form.setParameter(name, value)
