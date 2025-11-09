"""
Abstract base class for Ewoks-Orange widgets.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any
from typing import Callable
from typing import List
from typing import Mapping
from typing import Optional

from AnyQt import QtWidgets
from ewokscore import missing_data
from ewokscore.variable import value_from_transfer

from ...orange_version import ORANGE_VERSION

# OWBaseWidget: lowest level Orange widget base class
# OWWidget: highest level Orangewidget base class.
if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    from oasys.widgets.widget import OWWidget

    OWBaseWidget = OWWidget
elif ORANGE_VERSION == ORANGE_VERSION.latest_orange:
    from Orange.widgets.widget import OWWidget
    from orangewidget.widget import OWBaseWidget
else:
    from orangewidget.widget import OWBaseWidget

    OWWidget = OWBaseWidget

from ..orange_utils._signals import get_signal
from ..orange_utils.orange_imports import OWBaseWidget
from ..orange_utils.orange_imports import OWWidget
from ..orange_utils.signals import Output
from ..utils import invalid_data
from ..utils.events import scheme_ewoks_events
from .meta import OWEwoksWidgetMetaClass
from .meta import ow_build_opts

_logger = logging.getLogger(__name__)


class OWEwoksBaseWidget(OWWidget, metaclass=OWEwoksWidgetMetaClass, **ow_build_opts):
    """
    Abstract base class connecting Ewoks tasks with Orange workflow widgets.

    This class manages inputs (default and dynamic), constructs task arguments,
    and provides hooks for executing tasks and propagating outputs.

    Default input values are saved in the workflow file.
    Typically default input values are provided by the user through a widget component.

    Dynamic input values are not saved in the workflow file.
    Typically dynamic input values are send from the output if upstream tasks and wrapped
    by a `Variable` to handle things like Ewoks tasks output caching.

    Subclasses must implement:

    - methods: get_task_outputs, _execute_ewoks_task
    - properties: task_succeeded, task_done, task_exception
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize base widget internals.

        :param args: Positional args forwarded to parent.
        :param kwargs: Keyword args forwarded to parent.
        """
        super().__init__(*args, **kwargs)
        self.__dynamic_inputs = dict()
        self.__task_output_changed_callbacks: List[Callable[[], None]] = [
            self.task_output_changed
        ]
        self.__post_task_exception: Optional[Exception] = None

    # --- Control and Main area --------------------------------------------------------------

    def _init_control_area(self) -> None:
        """
        Initialize control area typically used for input controls and action buttons.

        Adds "Trigger" and "Execute" buttons wired to execution entry points.
        """
        layout = self._get_control_layout()

        trigger = QtWidgets.QPushButton("Trigger")
        execute = QtWidgets.QPushButton("Execute")

        layout.addWidget(trigger)
        trigger.released.connect(self.execute_ewoks_task)
        self._trigger_button = trigger

        layout.addWidget(execute)
        execute.released.connect(self.execute_ewoks_task_without_propagation)
        self._execute_button = execute

    def _init_main_area(self):
        """
        Initialize main area typically used to display results.
        """
        self._get_main_layout()

    def _get_control_layout(self):
        """
        Get or create the control area layout.

        :return: Qt layout instance for control area.
        """
        layout = self.controlArea.layout()
        # sp = self.controlArea.sizePolicy()
        # sp.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
        # self.controlArea.setSizePolicy(sp)
        # print("changed the size policy")
        if layout is None:
            layout = QtWidgets.QVBoxLayout()
            self.controlArea.setLayout(layout)
        return layout

    def _get_main_layout(self):
        """
        Get or create the main area layout.

        :raises RuntimeError: If the widget doesn't declare `want_main_area`.
        :return: Qt layout instance for main area.
        """
        if not self.want_main_area:
            raise RuntimeError(
                f"{type(self).__name__} must have class attribute `want_main_area = True`"
            )
        layout = self.mainArea.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout()
            self.mainArea.setLayout(layout)
        return layout

    # --- Ewoks task inputs --------------------------------------------------------------

    @classmethod
    def get_input_names(cls):
        """
        Return Ewoks task input names for the bound task class.

        :return: Iterable of input name strings.
        """
        return cls.ewokstaskclass.input_names()

    def get_task_inputs(self) -> dict:
        """
        Merge default and dynamic inputs producing the inputs mapping used by tasks.

        :return: Mapping of input name -> Variable or value (may include missing markers).
        """
        inputs = self.get_default_input_values()
        inputs.update(self.__dynamic_inputs)
        return inputs

    def get_task_input_values(self) -> dict:
        """
        Return all task input values (dynamic or default when missing).

        :return: Dict of input name -> plain value.
        """
        return {k: self._extract_value(v) for k, v in self.get_task_inputs().items()}

    def get_task_input_value(
        self, name: str, default: Any = missing_data.MISSING_DATA
    ) -> Any:
        """
        Retrieve a single task input value by name, returning default if missing.

        :param name: Input name.
        :param default: Fallback when missing.
        :return: The extracted input value or default.
        """
        adict = self.get_task_inputs()
        try:
            value = adict[name]
        except KeyError:
            return default
        value = self._extract_value(value)
        if missing_data.is_missing_data(value):
            return default
        return value

    # --- Ewoks task default inputs (SAVED IN FILE) --------------------------------------------------------------

    def get_default_input_names(self, include_missing: bool = False) -> set:
        """
        Return input names that have default values (or all input names).

        :param include_missing: If True return all defined input names.
        :return: Set of input names.
        """
        self._deprecated_default_inputs()
        if include_missing:
            return set(self.get_input_names())
        else:
            return set(self._ewoks_default_inputs)

    def get_default_input_values(
        self, include_missing: bool = False, defaults: Optional[Mapping] = None
    ) -> dict:
        """
        Return default input values or a mapping including missing markers.

        :param include_missing: If True include all input names set to INVALIDATION_DATA initially.
        :param defaults: Optional mapping of default overrides.
        :return: Dict of input name -> value or missing marker.
        """
        self._deprecated_default_inputs()
        if include_missing:
            values = {
                name: invalid_data.INVALIDATION_DATA for name in self.get_input_names()
            }
        else:
            values = dict()
        if defaults:
            values.update(defaults)
        values.update(self._ewoks_default_inputs)
        return {name: invalid_data.as_missing(value) for name, value in values.items()}

    def get_default_input_value(self, name: str, default: Any = None) -> Any:
        """
        Get a default input value saved in the widget settings.

        :param name: Input name.
        :param default: Fallback if the value is not present.
        :return: The default value or provided fallback.
        """
        return self._ewoks_default_inputs.get(name, default)

    def set_default_input(self, name: str, value: Any) -> None:
        """
        Set or remove a default input.

        :param name: Input name.
        :param value: Input value. If it's invalidation data the default is removed.
        """
        if invalid_data.is_invalid_data(value):
            _logger.debug("ewoks widget: remove default input %r", name)
            _ = self._ewoks_default_inputs.pop(name, None)
        else:
            _logger.debug("ewoks widget: set default input %r = %s", name, value)
            self._ewoks_default_inputs[name] = value

    def update_default_inputs(self, **inputs) -> None:
        """
        Batch-set default inputs.

        :param inputs: name=value pairs to set as defaults.
        """
        for name, value in inputs.items():
            self.set_default_input(name, value)

    def _deprecated_default_inputs(self):
        """
        Handle migration of deprecated `default_inputs` attribute to `_ewoks_default_inputs`.
        """
        adict = dict(self.default_inputs)
        if not adict:
            return
        self.default_inputs.clear()
        adict = {
            name: value
            for name, value in adict.items()
            if not invalid_data.is_invalid_data(value)
            and name not in self._ewoks_default_inputs
        }
        warnings.warn(
            ".ows file node property 'default_inputs' has been converted to '_ewoks_default_inputs'. Please save the workflow to keep this change.",
            DeprecationWarning,
        )
        self.update_default_inputs(**adict)

    # --- Ewoks task dynamic inputs (NOT SAVED IN FILE) --------------------------------------------------------------

    def get_dynamic_input_names(self, include_missing: bool = False) -> set:
        """
        Return input names that have dynamic variables (or all input names).

        :param include_missing: If True return all defined input names.
        :return: Set of input names.
        """
        if include_missing:
            return set(self.get_input_names())
        else:
            return set(self.__dynamic_inputs)

    def get_dynamic_input_values(
        self, include_missing: bool = False, defaults: Optional[Mapping] = None
    ) -> dict:
        """
        Return dynamic input values or a mapping including missing markers.

        :param include_missing: If True include all input names set to INVALIDATION_DATA initially.
        :param defaults: Optional mapping of default overrides.
        :return: Dict of input name -> value or missing marker.
        """
        if include_missing:
            values = {
                name: invalid_data.INVALIDATION_DATA for name in self.get_input_names()
            }
        else:
            values = dict()
        if defaults:
            values.update(defaults)
        values.update(
            {k: self._extract_value(v) for k, v in self.__dynamic_inputs.items()}
        )
        return {name: invalid_data.as_missing(value) for name, value in values.items()}

    def get_dynamic_input_value(self, name: str, default: Any = None) -> Any:
        """
        Get a dynamic input value provided by upstream nodes.

        :param name: Input name.
        :param default: Fallback if not present.
        :return: The dynamic value or provided fallback.
        """
        value = self.__dynamic_inputs.get(name, default)
        return self._extract_value(value)

    def set_dynamic_input(self, name: str, value: Any) -> None:
        """
        Set or remove a dynamic input variable (from upstream nodes).

        :param name: Input name.
        :param value: Input variable or value. Invalid data removes the dynamic input.
        """
        if invalid_data.is_invalid_data(value):
            _logger.debug("ewoks widget: remove dynamic input %r", name)
            _ = self.__dynamic_inputs.pop(name, None)
        else:
            _logger.debug(
                "ewoks widget: set dynamic input %r = %s",
                name,
                value_from_transfer(value, varinfo=self._ewoks_varinfo),
            )
            self.__dynamic_inputs[name] = value

    def update_dynamic_inputs(self, **inputs) -> None:
        """
        Batch-set dynamic inputs.

        :param inputs: name=value pairs to set as dynamic inputs.
        """
        for name, value in inputs.items():
            self.set_dynamic_input(name, value)

    def _extract_value(self, data) -> Any:
        """
        Convert transfer objects (Variable wrappers or raw values) to plain values.

        :param data: The transferred data.
        :return: Extracted underlying value.
        """
        return value_from_transfer(data, varinfo=self._ewoks_varinfo)

    def _receive_dynamic_input(self, name: str, value: Any) -> None:
        """
        Deprecated alias for setting a dynamic input.

        :param name: Input name.
        :param value: Input value.
        """
        warnings.warn(
            "`_receive_dynamic_input` is deprecated in favor of `set_dynamic_input`.",
            DeprecationWarning,
        )
        self.set_dynamic_input(name, value)

    # --- Ewoks task outputs --------------------------------------------------------------

    @classmethod
    def get_output_names(cls):
        """
        Return Ewoks task output names for the bound task class.

        :return: Iterable of output name strings.
        """
        return cls.ewokstaskclass.output_names()

    def get_task_outputs(self) -> dict:
        """
        Return task output variables.

        Subclasses must implement this to return a dict-like mapping of output name
        to Variable.
        """
        raise NotImplementedError("Base class")

    def get_task_output_values(self) -> dict:
        """
        Return all task output values extracted from Variables.

        :return: Dict of output name -> plain value (missing replaced).
        """
        return {k: self._extract_value(v) for k, v in self.get_task_outputs().items()}

    def get_task_output_value(
        self, name, default: Any = missing_data.MISSING_DATA
    ) -> Any:
        """
        Retrieve a single task output value by name, returning default if missing.

        :param name: Output name.
        :param default: Fallback when missing.
        :return: The extracted output value or default.
        """
        adict = self.get_task_outputs()
        try:
            value = adict[name]
        except KeyError:
            return default
        value = self._extract_value(value)
        if missing_data.is_missing_data(value):
            return default
        return value

    # --- Upstream and downstream signals --------------------------------------------------------------

    def handleNewSignals(self) -> None:
        """
        Called by Orange after all signal handlers have run to set dynamic inputs.

        Default implementation triggers task execution (with propagation).
        """
        self.execute_ewoks_task(log_missing_inputs=False)

    def propagate_downstream(self, succeeded: Optional[bool] = None) -> None:
        """
        Trigger downstream propagation: send outputs on success or invalidation on failure.

        :param succeeded: Optional override of the current task success flag.
        """
        if succeeded is None:
            succeeded = self.task_succeeded
        if succeeded:
            self.__post_task_execute([self.trigger_downstream])
        else:
            self.__post_task_execute([self.clear_downstream])

    def trigger_downstream(self) -> None:
        """
        Send the current task output variables downstream via Orange signals.

        Outputs set to invalidation data are sent as INVALIDATION_DATA.
        """
        _logger.debug("%s: trigger downstream", self)
        if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
            for ewoksname, var in self.get_task_outputs().items():
                output = self._get_output_signal(ewoksname)
                if invalid_data.is_invalid_data(var.value):
                    self.send(output.name, invalid_data.INVALIDATION_DATA)
                    # Note: perhaps `self.invalidate(output.name)` is equivalent
                else:
                    self.send(output.name, var)
        else:
            for ewoksname, var in self.get_task_outputs().items():
                output = self._get_output_signal(ewoksname)
                if invalid_data.is_invalid_data(var.value):
                    output.send(invalid_data.INVALIDATION_DATA)
                    # Note: perhaps `output.invalidate()` is equivalent
                else:
                    output.send(var)

    def clear_downstream(self) -> None:
        """
        Propagate INVALIDATION_DATA to all downstream outputs.

        Useful to indicate that this node's outputs are invalid (e.g., after failure).
        """
        _logger.debug("%s: clear downstream", self)
        if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
            for ewoksname in self.get_task_outputs():
                output = self._get_output_signal(ewoksname)
                self.send(output.name, invalid_data.INVALIDATION_DATA)
                # Note: perhaps `self.invalidate(output.name)` is equivalent
        else:
            for ewoksname in self.get_task_outputs():
                output = self._get_output_signal(ewoksname)
                output.send(invalid_data.INVALIDATION_DATA)
                # Note: perhaps `output.invalidate` is equivalent

    def _get_output_signal(self, ewoksname: str) -> Output:
        """
        Resolve and return the Orange output signal for a given Ewoks output name.

        :param ewoksname: Ewoks output name.
        :raises RuntimeError: If the corresponding Orange output signal does not exist.
        :return: The Orange signal object.
        """
        return get_signal(self, "outputs", ewoksname)

    # --- Ewoks task execution --------------------------------------------------------------

    @property
    def task_output_changed_callbacks(self) -> list:
        """
        Access the list of callbacks executed after task output change.

        :return: List of callables.
        """
        return self.__task_output_changed_callbacks

    def task_output_changed(self) -> None:
        """
        Default callback invoked when task output changed.

        Subclasses may override to react to this event.
        """
        pass

    def execute_ewoks_task(self, log_missing_inputs: bool = True) -> None:
        """
        Execute the Ewoks task and propagate downstream on completion.

        :param log_missing_inputs: Whether missing inputs should be logged.
        """
        _logger.debug("%s: execute ewoks task (with propagation)", self)
        self._execute_ewoks_task(propagate=True, log_missing_inputs=log_missing_inputs)

    def execute_ewoks_task_without_propagation(self) -> None:
        """
        Execute the Ewoks task without propagating outputs downstream.
        """
        _logger.debug("%s: execute ewoks task (without propagation)", self)
        self._execute_ewoks_task(propagate=False, log_missing_inputs=False)

    @property
    def task_succeeded(self) -> Optional[bool]:
        """
        Whether the most recent task execution succeeded.

        :return: True if succeeded, False if failed, or None if never run.
        """
        raise NotImplementedError("Base class")

    @property
    def task_done(self) -> Optional[bool]:
        """
        Whether the most recent task execution finished (success or failure).

        :return: True/False or None if never run.
        """
        raise NotImplementedError("Base class")

    @property
    def task_exception(self) -> Optional[Exception]:
        """
        Exception raised during the most recent task execution, if any.

        :return: Exception instance or None.
        """
        raise NotImplementedError("Base class")

    @property
    def post_task_exception(self) -> Optional[Exception]:
        """
        Exception raised while running post-task callbacks (if any).

        :return: Exception instance or None.
        """
        return self.__post_task_exception

    def _get_task_arguments(self) -> dict:
        """
        Build task constructor arguments.

        :return: Dict with inputs, varinfo, execinfo and node_id suitable for Task constructor.
        """
        if self.signalManager is None:
            execinfo = None
            node_id = None
        else:
            scheme = self.signalManager.scheme()
            node = scheme.node_for_widget(self)
            node_id = node.title
            if not node_id:
                node_id = scheme.nodes.index(node)
            execinfo = scheme_ewoks_events(scheme, self._ewoks_execinfo)

        if self._ewoks_task_options:
            task_arguments = dict(self._ewoks_task_options)
        else:
            task_arguments = dict()
        task_arguments.update(
            inputs=self.get_task_inputs(),
            varinfo=self._ewoks_varinfo,
            execinfo=execinfo,
            node_id=node_id,
        )
        return task_arguments

    def _output_changed(self) -> None:
        """
        Called when the Ewoks task execution finishes and outputs changed.

        This base class does not call it. It is up to the derived classes
        that implement `_execute_ewoks_task` to call it.

        This invokes registered post-task callbacks.
        """
        self.__post_task_execute(self.__task_output_changed_callbacks)

    def __post_task_execute(self, callbacks: List[Callable[[], None]]) -> None:
        """
        Execute a list of callbacks sequentially.

        If a callback raises, it is stored in :attr:`__post_task_exception` and re-raised.

        :param callbacks: List of zero-argument callables to invoke.
        """
        ncallbacks = len(callbacks)
        if ncallbacks == 0:
            return
        try:
            callbacks[0]()
        except Exception as e:
            self.__post_task_exception = e
            raise
        finally:
            if ncallbacks > 1:
                self.__post_task_execute(callbacks[1:])

    def _execute_ewoks_task(self, propagate: bool, log_missing_inputs: bool) -> None:
        """
        Subclasses must implement how the task is created and executed.

        :param propagate: Whether to propagate outputs downstream after execution.
        :param log_missing_inputs: Whether to log missing input warnings.
        """
        raise NotImplementedError("Base class")
