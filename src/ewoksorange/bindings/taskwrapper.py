from numbers import Number
from typing import List, Mapping, Optional, Tuple, Type

from ewoksutils.import_utils import qualname
from ewoksutils.import_utils import import_qualname
from ewokscore import Task
from ewokscore.variable import value_from_transfer

from .qtapp import ensure_qtapp
from .qtapp import process_qtapp_events
from .qtapp import QtEvent
from .owwidgets import is_ewoks_widget_class
from .owwidgets import is_native_widget_class
from .owwidgets import OWEwoksBaseWidget
from .owwidgets import OWBaseWidget
from . import owsignals
from . import owsettings
from . import invalid_data
from .owsignal_manager import SignalManagerWithoutScheme
from .owsignal_manager import set_input_value
from ..orange_version import ORANGE_VERSION

__all__ = ["OWWIDGET_TASKS_GENERATOR"]


def owwidget_task_wrapper(widget_qualname: str) -> Task:
    """Create a task that does the computation through an orange widget.
    When the widget is an ewoks widget, still use the widget and not
    the corresponding task class directly.
    """
    widget_class = import_qualname(widget_qualname)
    registry_name = widget_qualname + ".wrapper"
    if registry_name in Task.get_subclass_names():
        return Task.get_subclass(registry_name)

    if is_ewoks_widget_class(widget_class):
        return _ewoks_owwidget_task_wrapper(registry_name, widget_class)
    elif is_native_widget_class(widget_class):
        return _native_owwidget_task_wrapper(registry_name, widget_class)
    else:
        raise TypeError(widget_class, "expected to be an OWWidget")


OWWIDGET_TASKS_GENERATOR = qualname(owwidget_task_wrapper)


def _ewoks_owwidget_task_wrapper(registry_name, widget_class) -> Task:
    """Wrap an Ewoks widget with an Ewoks task"""
    all_input_names = widget_class.get_input_names()
    try:
        ewokstaskclass = widget_class.ewokstaskclass
        input_names = ewokstaskclass.required_input_names()
        optional_input_names = ewokstaskclass.optional_input_names()
        expected = set(input_names) | set(optional_input_names)
        assert all_input_names == expected
    except AttributeError:
        input_names = all_input_names
        optional_input_names = tuple()
    output_names = widget_class.get_output_names()

    class WrapperTask(
        Task,
        input_names=input_names,
        optional_input_names=optional_input_names,
        output_names=output_names,
        registry_name=registry_name,
    ):
        def run(self):
            output_values = execute_ewoks_owwidget(
                widget_class, inputs=self.input_values
            )
            for k, v in output_values.items():
                self.output_variables[k].value = v

    return WrapperTask


def _native_owwidget_task_wrapper(registry_name, widget_class) -> Task:
    """Wrap a native Orange widget with an Ewoks task"""
    input_signals = owsignals.get_signals(widget_class.Inputs)
    optional_input_names = set(input_signals.keys())
    output_signals = owsignals.get_signals(widget_class.Outputs)
    output_names = set(output_signals.keys())
    input_names = tuple()

    class WrapperTask(
        Task,
        input_names=input_names,
        optional_input_names=optional_input_names,
        output_names=output_names,
        registry_name=registry_name,
    ):
        def run(self):
            output_values = execute_native_owwidget(
                widget_class, inputs=self.input_values
            )
            for k, v in output_values.items():
                self.output_variables[k].value = v

    return WrapperTask


def instantiate_owwidget(
    widget_class: Type[OWBaseWidget],
    signal_manager=None,
    stored_settings: Optional[Mapping] = None,
):
    if stored_settings:
        stored_settings = {
            k: v
            for k, v in stored_settings.items()
            if not invalid_data.is_invalid_data(v)
        }
    widget = widget_class.__new__(
        widget_class, signal_manager=signal_manager, stored_settings=stored_settings
    )
    widget.__init__()
    return widget


def execute_ewoks_owwidget(
    widget_class: Type[OWEwoksBaseWidget],
    inputs: Optional[Mapping] = None,
    timeout: Optional[Number] = None,
) -> dict:
    ensure_qtapp()
    result = dict()
    widget = instantiate_owwidget(widget_class)

    try:
        # Receive and store results
        outputsReceived = QtEvent()

        def _output_cb():
            try:
                result.update(widget.get_task_output_values())
            finally:
                outputsReceived.set()

        widget.task_output_changed_callbacks.add(_output_cb)

        # Call the input setters
        if inputs:
            if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
                signals = widget.inputs
            else:
                signals = widget.get_signals("inputs")
            orange_to_ewoks = owsignals.get_orange_to_ewoks_mapping(
                widget_class, "inputs"
            )

            for index, signal in enumerate(signals):
                if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
                    key = orange_to_ewoks.get(signal.name, signal.name)
                else:
                    key = signal.ewoksname
                if key in inputs:
                    value = value_from_transfer(inputs[key])
                    set_input_value(widget, signal, value, index)

        # Start calculation
        widget.handleNewSignals()

        # Wait for the result
        outputsReceived.wait(timeout=timeout)
    finally:
        widget.close()
    return result


def execute_native_owwidget(
    widget_class: Type[OWBaseWidget], inputs: Optional[Mapping] = None
):
    ensure_qtapp()
    result = dict()

    output_signals = owsignals.get_signals(widget_class.Outputs)
    orange_to_ewoks_namemap = {
        ewoks_name: signal.name for ewoks_name, signal in output_signals.items()
    }

    input_list, stored_settings = _parse_input_values(widget_class, inputs)

    # Create widget with the proper settings
    widget = instantiate_owwidget(
        widget_class,
        signal_manager=SignalManagerWithoutScheme(),
        stored_settings=stored_settings,
    )
    try:
        # Call input setters
        for index, (signal, value) in enumerate(input_list):
            set_input_value(widget, signal, value, index)

        # Start calculation
        widget.handleNewSignals()

        # Wait for the result
        process_qtapp_events()

        # Fetch outputs
        for ewoks_name, orange_name in orange_to_ewoks_namemap.items():
            value = widget.signalManager.get_output_value(
                widget, orange_name, timeout=None
            )
            result[ewoks_name] = value
    finally:
        widget.close()
    return result


def _parse_input_values(
    widget_class, inputs: Optional[Mapping] = None
) -> Tuple[List, dict]:
    used_values = set()
    settings_dict = dict()
    input_list = list()

    # Values corresponding to settings
    setting_names = list(owsettings.get_settings(widget_class))
    for ewoksname in setting_names:
        if ewoksname not in inputs:
            continue
        used_values.add(ewoksname)
        value = value_from_transfer(inputs[ewoksname])
        settings_dict[ewoksname] = value

    # Values corresponding to inputs
    for signal in widget_class.get_signals("inputs"):
        ewoksname = owsignals.signal_orange_to_ewoks_name(
            widget_class, "inputs", signal.name
        )
        if ewoksname not in inputs:
            continue
        used_values.add(ewoksname)
        value = value_from_transfer(inputs[ewoksname])
        input_list.append((signal, value))

    # Node properties not corresponding to settings or inputs
    # are used in settings migration
    unused_values = set(inputs.keys()) - used_values
    for ewoksname in unused_values:
        value = value_from_transfer(inputs[ewoksname])
        settings_dict[ewoksname] = value

    return input_list, settings_dict
