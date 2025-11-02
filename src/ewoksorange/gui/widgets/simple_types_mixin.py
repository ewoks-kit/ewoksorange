from ..orange_utils.orange_imports import gui
from .parameter_form import ParameterForm


class SimpleTypesWidgetMixin:
    def __init__(self):
        super().__init__()
        self._init_control_area()
        self._init_main_area()

    def _init_control_area(self):
        super()._init_control_area()
        box = gui.widgetBox(self.controlArea, "Default Inputs")
        self._default_inputs_form = ParameterForm(parent=box)

        for name, value in self.get_default_input_values(include_missing=True).items():
            options = self._get_parameter_options(name)
            self._default_inputs_form.addParameter(
                name,
                value=value,
                value_change_callback=self._default_inputs_changed,
                **options,
            )

        box = gui.widgetBox(self.controlArea, "Inputs From Previous Task")
        self._dynamic_input_form = ParameterForm(parent=box)
        for name in self.get_input_names():
            options = self._get_parameter_options(name)
            self._dynamic_input_form.addParameter(
                name, readonly=True, enabled=False, **options
            )

    def _init_main_area(self):
        super()._init_main_area()
        box = gui.widgetBox(self.mainArea, "Outputs")
        self._output_form = ParameterForm(parent=box)
        for name in self.get_output_names():
            options = self._get_parameter_options(name)
            self._output_form.addParameter(name, readonly=True, **options)

    def _get_parameter_options(self, name):
        return {}

    def _default_inputs_changed(self):
        self.update_default_inputs(**self._default_inputs_form.get_parameter_values())

    def handleNewSignals(self):
        names = set(self.get_input_names())
        for name, value in self.get_dynamic_input_values().items():
            names.remove(name)
            self._dynamic_input_form.set_parameter_enabled(name, True)
            self._default_inputs_form.set_parameter_enabled(name, False)
            self._dynamic_input_form.set_parameter_value(name, value)
        for name in names:
            self._dynamic_input_form.set_parameter_enabled(name, False)
            self._default_inputs_form.set_parameter_enabled(name, True)
        super().handleNewSignals()

    def task_output_changed(self):
        for name, value in self.get_task_output_values().items():
            self._output_form.set_parameter_value(name, value)
        super().task_output_changed()


class IntegerAdderMixin(SimpleTypesWidgetMixin):
    def _get_parameter_options(self, name):
        return {"value_for_type": 0}
