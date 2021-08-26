from Orange.widgets.widget import OWWidget
from ewokscore import Task
from ewokscore.utils import qualname
from ewokscore.utils import import_qualname
from ewokscore.variable import value_from_transfer
from .qtapp import ensure_qtapp
from ewoksorange.bindings.qtapp import QtEvent


__all__ = ["OWWIDGET_TASKS_GENERATOR"]


def owwidget_task_wrapper(widget_qualname: str) -> Task:
    widget_class = import_qualname(widget_qualname)
    try:
        is_widget = issubclass(widget_class, OWWidget)
    except TypeError:
        is_widget = False
    if not is_widget:
        raise TypeError(widget_class, "expected to be an OWWidget")

    registry_name = widget_qualname + ".wrapper"
    if registry_name in Task.get_subclass_names():
        return Task.get_subclass(registry_name)

    all_input_names = widget_class.input_names()
    try:
        ewokstaskclass = widget_class.ewokstaskclass
        input_names = ewokstaskclass.required_input_names()
        optional_input_names = ewokstaskclass.optional_input_names()
        expected = set(input_names) | set(optional_input_names)
        assert all_input_names == expected
    except AttributeError:
        input_names = all_input_names
        optional_input_names = None

    class WrapperTask(
        Task,
        input_names=input_names,
        optional_input_names=optional_input_names,
        output_names=widget_class.output_names(),
        registry_name=registry_name,
    ):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            ensure_qtapp()
            self.outputsReceived = QtEvent()
            self.widget = widget_class()
            self.widget.ewoks_output_callbacks = (self.receiveOutputSend,)

        def run(self):
            # Trigger the input handlers
            values = self.input_values
            for signal in self.widget.get_signals("inputs"):
                handler = getattr(self.widget, signal.handler)
                handler(values[signal.ewoksname])

            # Send the outputs
            self.widget.handleNewSignals()

            self.outputsReceived.wait()

        def receiveOutputSend(self, values):
            try:
                for name, value in values.items():
                    self.output_variables[name].value = value_from_transfer(value)
            finally:
                self.outputsReceived.set()

    return WrapperTask


OWWIDGET_TASKS_GENERATOR = qualname(owwidget_task_wrapper)
