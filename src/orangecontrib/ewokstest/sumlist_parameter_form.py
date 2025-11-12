import json

from ewoksorange.gui.owwidgets.nothread import OWEwoksWidgetNoThread
from ewoksorange.gui.widgets.parameter_form import ParameterForm
from ewoksorange.tests.examples.tasks import SumList4


class OWSumList(
    OWEwoksWidgetNoThread,
    ewokstaskclass=SumList4,
):
    name = "SumList parameter form"
    description = "Showcase form genereration to supply a list to sum"
    icon = "icons/mywidget.svg"
    want_main_area = True

    def __init__(self):
        super().__init__()
        self._init_control_area()
        self._parameter_form = ParameterForm(parent=self.controlArea)

        self._parameter_form.addParameter(
            "delay",
            label="Delay for each sum iteration",
            value_for_type=0,
            value_change_callback=self._inputs_changed,
        )

        self._parameter_form.addParameter(
            "list",
            label="List of elements to sum",
            value_for_type="",
            serialize=json.dumps,
            deserialize=json.loads,
            value_change_callback=self._inputs_changed,
        )
        self._parameter_form.addStretch()
        self._update_parameter_values()

    def _inputs_changed(self):
        new_values = self._parameter_form.get_parameter_values()
        self.update_default_inputs(**new_values)

    def _update_parameter_values(self):
        new_values = self._parameter_form.get_parameter_values()
        self.update_default_inputs(**new_values)
