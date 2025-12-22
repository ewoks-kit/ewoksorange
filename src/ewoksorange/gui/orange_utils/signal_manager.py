import weakref
from typing import Any

from ...orange_version import ORANGE_VERSION

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    import AnyQt.QtCore  # noqa: F401 isort: skip  Needed for "import sip"
    import oasys.canvas.widgetsscheme as widgetsscheme_module
    from oasys.canvas.widgetsscheme import (
        OASYSSignalManager as _SignalManagerWithSchemeOrg,
    )

    class _SignalManagerWithScheme(_SignalManagerWithSchemeOrg):
        def has_pending(self):
            return bool(self._input_queue)

    notify_input_helper = None
else:
    from orangewidget.workflow.widgetsscheme import (
        WidgetsSignalManager as _SignalManagerWithScheme,
    )
    import orangewidget.workflow.widgetsscheme as widgetsscheme_module
    from orangewidget.utils.signals import notify_input_helper

from ewokscore.variable import Variable
from ewokscore.variable import value_from_transfer
from orangecanvas.scheme import signalmanager

from ..owwidgets.types import is_native_widget
from ..qt_utils.app import QtEvent
from ..utils import invalid_data
from ._signals import get_signal_orange_names

# monkey patch of 'can_enable_dynamic' See https://gitlab.esrf.fr/workflow/ewoks/ewoksorange/-/issues/58

_super_can_enable_dynamic = signalmanager.can_enable_dynamic


def can_enable_dynamic_patch(link, value):
    # type: (SchemeLink, Any) -> bool
    """
    Can the a dynamic `link` (:class:`SchemeLink`) be enabled for `value`.
    """
    if isinstance(value, Variable):
        value = value.value
    return _super_can_enable_dynamic(link, value)


signalmanager.can_enable_dynamic = can_enable_dynamic_patch

# end monkey patch


class _MissingSignalValue:
    """Indicates a missing signal value and supports waiting for the real signal value"""

    completed = QtEvent()


class _OwWidgetSignalValues:
    """Store signal values and support waiting for a value"""

    def __init__(self):
        self._values = dict()

    def _get_value(self, signal_name) -> Any:
        if not isinstance(signal_name, str):
            signal_name = signal_name.name
        if signal_name not in self._values:
            self._values[signal_name] = _MissingSignalValue()
        return self._values[signal_name]

    def _set_value(self, signal_name, value) -> None:
        if not isinstance(signal_name, str):
            signal_name = signal_name.name
        self._values[signal_name] = value

    def set_value(self, signal_name, value) -> None:
        previous_value = self._get_value(signal_name)
        self._set_value(signal_name, value)
        if isinstance(previous_value, _MissingSignalValue):
            previous_value.completed.set()

    def invalidate_value(self, signal_name) -> None:
        previous_value = self._get_value(signal_name)
        if isinstance(previous_value, _MissingSignalValue):
            return
        self.set_value(signal_name, _MissingSignalValue())

    def get_value(self, signal_name, timeout=None) -> Any:
        value = self._get_value(signal_name)
        if isinstance(value, _MissingSignalValue):
            value.completed.wait(timeout=timeout)
            value = self._get_value(signal_name)
        return value

    def has_value(self, signal_name) -> bool:
        value = self._get_value(signal_name)
        return not isinstance(value, _MissingSignalValue)

    def has_values(self) -> bool:
        return bool(self._values)


class _OwWidgetSignalState:
    """Store input and output signal values for one widget and support waiting for a value"""

    def __init__(self, owwidget, *args, **kwargs):
        output_variable_names = get_signal_orange_names(owwidget, "outputs")
        widget_has_outputs = bool(output_variable_names)
        if not output_variable_names:
            output_variable_names = get_signal_orange_names(owwidget, "inputs")

        self._variable_names = output_variable_names
        self._widget_has_outputs = widget_has_outputs
        self._input_values = _OwWidgetSignalValues()
        self._output_values = _OwWidgetSignalValues()
        super().__init__(*args, **kwargs)

    def set_output_value(self, signal_name, value) -> None:
        self._output_values.set_value(signal_name, value)

    def invalidate_output_value(self, signal_name) -> None:
        self._output_values.invalidate_value(signal_name)

    def get_output_value(self, signal_name, timeout=None) -> Any:
        return self._output_values.get_value(signal_name, timeout=timeout)

    def has_output_value(self, signal_name) -> bool:
        return self._output_values.has_value(signal_name)

    def has_output_values(self) -> bool:
        return self._output_values.has_values()

    def set_input_value(self, signal_name, value) -> None:
        self._input_values.set_value(signal_name, value)

    def invalidate_input_value(self, signal_name) -> None:
        self._input_values.invalidate_value(signal_name)

    def get_input_value(self, signal_name, timeout=None) -> Any:
        return self._input_values.get_value(signal_name, timeout=timeout)

    def has_input_value(self, signal_name) -> bool:
        return self._input_values.has_value(signal_name)

    def has_input_values(self) -> bool:
        return self._input_values.has_values()

    def is_executed(self) -> bool:
        if self._variable_names:
            if self._widget_has_outputs:
                # Widget is executed when all outputs are set
                return all(
                    (self.has_output_value(name) for name in self._variable_names)
                )
            # Widget is executed when all inputs are set
            return all((self.has_input_value(name) for name in self._variable_names))

        # Task has no inputs or outputs
        return self.has_output_values() or self.has_input_values()


class SignalManagerWithOutputTracking:
    """Store input and output signal value per widget. Knows
    when a widget is "executed" or not.

    Losely based on Orange.widgets.tests.base.DummySignalManager
    """

    def __init__(self, *args, **kwargs):
        self._widget_states = weakref.WeakKeyDictionary()
        super().__init__(*args, **kwargs)

    def _get_widget_state(self, owwidget) -> _OwWidgetSignalState:
        state = self._widget_states.get(owwidget, None)
        if state is not None:
            return state
        state = _OwWidgetSignalState(owwidget)
        self._widget_states[owwidget] = state
        return state

    def set_output_value(self, owwidget, signal_name, value) -> None:
        self._get_widget_state(owwidget).set_output_value(signal_name, value)

    def invalidate_output_value(self, owwidget, signal_name) -> None:
        self._get_widget_state(owwidget).invalidate_output_value(signal_name)

    def get_output_value(self, owwidget, signal_name, timeout=None) -> Any:
        return self._get_widget_state(owwidget).get_output_value(
            signal_name, timeout=timeout
        )

    def has_output_value(self, owwidget, signal_name) -> bool:
        return self._get_widget_state(owwidget).has_output_value(signal_name)

    def set_input_value(self, owwidget, signal_name, value) -> None:
        self._get_widget_state(owwidget).set_input_value(signal_name, value)

    def invalidate_input_value(self, owwidget, signal_name) -> None:
        self._get_widget_state(owwidget).invalidate_input_value(signal_name)

    def get_input_value(self, owwidget, signal_name, timeout=None) -> Any:
        return self._get_widget_state(owwidget).get_input_value(
            signal_name, timeout=timeout
        )

    def has_input_value(self, owwidget, signal_name) -> bool:
        return self._get_widget_state(owwidget).has_input_value(signal_name)

    def widget_is_executed(self, owwidget) -> bool:
        return self._get_widget_state(owwidget).is_executed()


class SignalManagerWithoutScheme(SignalManagerWithOutputTracking):
    """Used when no Orange canvas is present.

    Only needs to keep track of widget outputs because data between tasks
    is passed by the Ewoks mechanism, not the Orange mechanism (signal manager).
    """

    def send(self, owwidget, signal_name, value, *args, **kwargs) -> None:
        self.set_output_value(owwidget, signal_name, value)


class SignalManagerWithScheme(
    SignalManagerWithOutputTracking, _SignalManagerWithScheme
):
    """Used when the Orange canvas is present.

    Dereference `Variable` types for native Orange widget inputs.
    """

    def send(self, owwidget, signal_name, value, *args, **kwargs) -> None:
        super().send(owwidget, signal_name, value, *args, **kwargs)
        self.set_output_value(owwidget, signal_name, value)

    def process_signals_for_widget(self, node, owwidget, signals) -> None:
        for signal in signals:
            if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
                signal_name = signal.link.sink_channel
            else:
                signal_name = signal.channel.name
            self.set_input_value(owwidget, signal_name, signal.value)
        if is_native_widget(owwidget):
            modified_signals = list()
            for signal in signals:
                sinfo = signal._asdict()
                sinfo["value"] = value_from_transfer(sinfo["value"])
                modified_signals.append(type(signal)(**sinfo))
            signals = modified_signals
        super().process_signals_for_widget(node, owwidget, signals)

    def invalidate(self, node, channel) -> None:
        super().invalidate(node, channel)
        owwidget = self.scheme().widget_for_node(node)
        if owwidget is None:
            return
        self.invalidate_input_value(owwidget, channel.name, _MissingSignalValue())

    def widget_is_finished(self, owwidget) -> bool:
        """Widget is executed for the last time and will not be execute again"""
        if self.has_pending():
            return False  # The widget might be executed again
        return super().widget_is_executed(owwidget)


def set_input_value(owwidget, signal, value, index) -> None:
    value = invalid_data.as_invalidation(value)
    key = id(owwidget), signal.name, signal.id
    if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
        handler = getattr(owwidget, signal.handler)
        handler(value)
    else:
        notify_input_helper(signal, owwidget, value, key=key, index=index)


def patch_signal_manager():
    if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
        widgetsscheme_module.OASYSSignalManager = SignalManagerWithScheme
    else:
        widgetsscheme_module.WidgetsSignalManager = SignalManagerWithScheme
