"""
Base class for Ewoks-Orange widgets.
"""

import functools
import logging
import multiprocessing
import multiprocessing.context
import warnings
from concurrent import futures
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Mapping
from typing import Optional
from typing import Set

from AnyQt import QtWidgets
from ewokscore import missing_data
from ewokscore.variable import Variable
from ewokscore.variable import VariableContainer
from ewokscore.variable import value_from_transfer

from ...orange_version import ORANGE_VERSION
from ..utils.invalid_data import is_invalid_data

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

from ..concurrency.executor import Concurrency
from ..concurrency.executor import EwoksExecutor
from ..concurrency.executor import SubmitPolicy
from ..concurrency.executor import TaskFuture
from ..concurrency.executor import create_pool_executor
from ..orange_utils._signals import get_signal
from ..orange_utils.orange_imports import OWBaseWidget
from ..orange_utils.orange_imports import OWWidget
from ..orange_utils.signals import Output
from ..qt_utils.progress import QProgress
from ..utils import invalid_data
from ..utils.events import scheme_ewoks_events
from ..utils.model import get_model_default_values
from .meta import OWEwoksWidgetMetaClass
from .meta import ow_build_opts

_logger = logging.getLogger(__name__)


class OWEwoksBaseWidget(OWWidget, metaclass=OWEwoksWidgetMetaClass, **ow_build_opts):
    """
    Base class connecting Ewoks tasks with Orange workflow widgets.

    This class manages inputs (default and dynamic), executes the Ewoks task
    through an :class:`~ewoksorange.gui.concurrency.executor.EwoksExecutor` and
    propagates the outputs downstream.

    Default input values are saved in the workflow file.
    Typically default input values are provided by the user through a widget component.

    Dynamic input values are not saved in the workflow file.
    Typically dynamic input values are send from the output if upstream tasks and wrapped
    by a `Variable` to handle things like Ewoks tasks output caching.

    The Ewoks task class and the execution strategy are provided as class arguments:

    .. code-block:: python

        class MyOwWidget(
            OWEwoksBaseWidget,
            ewokstaskclass=MyTask,
            concurrency="thread",
            max_workers=1,
            submit_policy="always",
            mp_context="spawn",
        ):
            ...

    The defaults execute tasks one-at-a-time in a single background thread,
    queueing submissions that arrive while busy.
    """

    _CONCURRENCY: Concurrency = Concurrency.THREAD
    """Task execution backend, provided by the `concurrency` class argument.

    - `Concurrency.SYNC` (`"sync"`): execute in the calling (GUI) thread.
    - `Concurrency.THREAD` (`"thread"`): execute in a thread pool.
    - `Concurrency.PROCESS` (`"process"`): execute in a process pool. This requires
      all task inputs and outputs to be picklable.
    """

    _MAX_WORKERS: Optional[int] = 1
    """Maximum number of task workers, provided by the `max_workers` class argument.
    Ignored for `Concurrency.SYNC`.

    - `1`: execute one task at a time.
    - `n > 1`: execute at most `n` tasks at a time.
    - `None`: use the pool default.
    """

    _SUBMIT_POLICY: SubmitPolicy = SubmitPolicy.ALWAYS
    """What to do with a task submission while the executor is busy, provided by
    the `submit_policy` class argument.

    - `SubmitPolicy.ALWAYS` (`"always"`): submit, so it runs when a worker is free.
    - `SubmitPolicy.DROP_IF_BUSY` (`"drop_if_busy"`): drop the submission.
    """

    _MP_CONTEXT: Optional[multiprocessing.context.BaseContext] = (
        multiprocessing.get_context("spawn")
    )
    """Multiprocessing context for the task workers and their IPC manager, provided
    by the `mp_context` class argument as a context or a start method name. Only
    used for `Concurrency.PROCESS`.

    Defaults to `"spawn"`: a Qt application is always multi-threaded and libraries
    commonly used by Ewoks tasks (HDF5 in particular) are not fork-safe. Use
    `mp_context=None` for the platform default instead, which is `"fork"` on Linux.
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

        self.__taskProgress = QProgress()
        self.__taskProgress.sigProgressChanged.connect(self._onProgressChanged)

        self.__executor = EwoksExecutor(
            self._create_pool_executor(),
            self._SUBMIT_POLICY,
            mp_context=self._MP_CONTEXT,
        )
        self.__executor.submitted.connect(self.__on_submitted)
        self.__executor.started.connect(self.__on_started)
        self.__executor.succeeded.connect(self.__on_succeeded)
        self.__executor.failed.connect(self.__on_failed)

        self.__propagate_by_future: Dict[TaskFuture, bool] = {}
        self.__propagate_next: bool = False

        self.__last_output_variables: Optional[VariableContainer] = None
        self.__last_task_succeeded: Optional[bool] = None
        self.__last_task_done: Optional[bool] = None
        self.__last_task_exception: Optional[Exception] = None

        # Note: this might be removed in the future. Please avoid using it.
        self.__current_task_future: Optional[TaskFuture] = None

    @classmethod
    def _create_pool_executor(cls) -> Optional[futures.Executor]:
        """
        Create the `concurrent.futures` executor that runs the Ewoks tasks.

        Override to execute tasks in an executor that :class:`Concurrency` does
        not cover.

        :return: An executor or `None` to execute in the calling thread.
        """
        return create_pool_executor(cls._CONCURRENCY, cls._MAX_WORKERS, cls._MP_CONTEXT)

    def onDeleteWidget(self):
        """
        Release the task executor and progress handling when the widget is removed.
        """
        self.__taskProgress.sigProgressChanged.disconnect(self._onProgressChanged)
        self._cleanup_task_executor()
        super().onDeleteWidget()

    def _cleanup_task_executor(self) -> None:
        """
        Shut down the task executor without waiting for pending tasks.
        """
        self.__executor.shutdown(wait=False)
        self.__executor = None

    def _onProgressChanged(self, progress: int):
        """
        Forward Ewoks task progress to the Orange progress bar.

        :param progress: Progress percentage.
        """
        self.progressBarSet(float(progress))

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
    def get_input_names(cls, exclude_hidden: bool = False) -> Set[str]:
        """
        Return Ewoks task input names for the bound task class.

        :return: Iterable of input name strings.
        """
        names = set(cls.ewokstaskclass.input_names())
        if exclude_hidden:
            names -= set(cls._ewoks_inputs_to_hide_from_orange)
        return names

    def get_task_inputs(self, exclude_hidden: bool = False) -> dict:
        """
        Merge default and dynamic inputs producing the inputs mapping used by tasks.

        :return: Mapping of input name -> Variable or value (may include missing markers).
        """
        inputs = self.get_default_input_values()
        inputs.update(self.__dynamic_inputs)
        if exclude_hidden:
            inputs = {
                k: v
                for k, v in inputs.items()
                if k not in self._ewoks_inputs_to_hide_from_orange
            }
        return inputs

    def get_task_input_values(self, exclude_hidden: bool = False) -> dict:
        """
        Return all task input values (dynamic or default when missing).

        :return: Dict of input name -> plain value.
        """
        return {
            k: self._extract_value(v)
            for k, v in self.get_task_inputs(exclude_hidden=exclude_hidden).items()
        }

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

    def get_default_input_names(
        self, include_missing: bool = False, exclude_hidden: bool = False
    ) -> Set[str]:
        """
        Return input names that have default values (or all input names).

        :param include_missing: If True return all defined input names.
        :return: Set of input names.
        """
        self._deprecated_default_inputs()
        if include_missing:
            names = set(self.get_input_names())
        else:
            names = set(self._ewoks_default_inputs)
        if exclude_hidden:
            names -= set(self._ewoks_inputs_to_hide_from_orange)
        return names

    @functools.lru_cache(maxsize=1)
    def _get_pydantic_model_default_values(self) -> dict:
        """
        Return default values defined in the task pydantic input model.
        """
        input_model = self.ewokstaskclass.input_model()

        if input_model is None:
            return {}

        # remove Values set to None or MISSING_DATA. This defines "invalid downstream" in Orange.
        return dict(
            filter(
                lambda pair: not is_invalid_data(pair[1]),
                get_model_default_values(input_model).items(),
            )
        )

    def get_default_input_values(
        self,
        include_missing: bool = False,
        defaults: Optional[Mapping] = None,
        exclude_hidden: bool = False,
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

        explicit_values = self._get_pydantic_model_default_values()
        values.update(explicit_values)

        if defaults:
            values.update(defaults)
        values.update(self._ewoks_default_inputs)

        if exclude_hidden:
            values = {
                k: v
                for k, v in values.items()
                if k not in self._ewoks_inputs_to_hide_from_orange
            }

        return {name: invalid_data.as_missing(value) for name, value in values.items()}

    def get_default_input_value(self, name: str, default: Any = None) -> Any:
        """
        Get a default input value saved in the pydantic models then updated by the widget settings.

        :param name: Input name.
        :param default: Fallback if the value is not present.
        :return: The default value or provided fallback.
        """
        values = self._get_pydantic_model_default_values()
        values.update(self._ewoks_default_inputs)
        return values.get(name, default)

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

    def get_dynamic_input_names(
        self, include_missing: bool = False, exclude_hidden: bool = False
    ) -> set:
        """
        Return input names that have dynamic variables (or all input names).

        :param include_missing: If True return all defined input names.
        :return: Set of input names.
        """
        if include_missing:
            names = set(self.get_input_names())
        else:
            names = set(self.__dynamic_inputs)
        if exclude_hidden:
            names -= set(self._ewoks_inputs_to_hide_from_orange)
        return names

    def get_dynamic_input_values(
        self,
        include_missing: bool = False,
        defaults: Optional[Mapping] = None,
        exclude_hidden: bool = False,
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

        if exclude_hidden:
            values = {
                k: v
                for k, v in values.items()
                if k not in self._ewoks_inputs_to_hide_from_orange
            }

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
    def get_output_names(cls, exclude_hidden: bool = False) -> Set[str]:
        """
        Return Ewoks task output names for the bound task class.

        :return: Iterable of output name strings.
        """
        names = set(cls.ewokstaskclass.output_names())
        if exclude_hidden:
            names -= set(cls._ewoks_outputs_to_hide_from_orange)
        return names

    def get_task_outputs(self, exclude_hidden: bool = False) -> Mapping[str, Variable]:
        """
        Return task output variables.

        :param exclude_hidden: Leave out the outputs hidden from Orange.
        :return: The task's :class:`~ewokscore.variable.VariableContainer`, or a
                 plain mapping when there are no outputs or when outputs were
                 filtered out. The filtered result is deliberately not a
                 `VariableContainer`: a new container would be a different
                 hashable with its own `uhash`, while these are still the
                 variables of the original one.
        """
        outputs = self._get_task_outputs()
        if outputs is None:
            return dict()
        if exclude_hidden:
            outputs = {
                k: v
                for k, v in outputs.items()
                if k not in self._ewoks_outputs_to_hide_from_orange
            }
        return outputs

    def _get_task_outputs(self) -> Optional[VariableContainer]:
        """
        Return the output variables produced by the last executed task.

        :return: The task's :class:`~ewokscore.variable.VariableContainer`, or
                 `None` when the last task failed or no task ran yet. An empty
                 container cannot express that: it holds `MISSING_DATA` instead
                 of a mapping, so `[]` and `in` raise `TypeError` on it.
        """
        return self.__last_output_variables

    def get_task_output_values(self, exclude_hidden: bool = False) -> dict:
        """
        Return all task output values extracted from Variables.

        :return: Dict of output name -> plain value (missing replaced).
        """
        return {
            k: self._extract_value(v)
            for k, v in self.get_task_outputs(exclude_hidden=exclude_hidden).items()
        }

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
            warnings.warn(
                "'succeeded' should be always provided from version 7.0.",
                DeprecationWarning,
            )
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
            for ewoksname, var in self.get_task_outputs(exclude_hidden=True).items():
                output = self._get_output_signal(ewoksname)
                if invalid_data.is_invalid_data(var.value):
                    self.send(output.name, invalid_data.INVALIDATION_DATA)
                    # Note: perhaps `self.invalidate(output.name)` is equivalent
                else:
                    self.send(output.name, var)
        else:
            for ewoksname, var in self.get_task_outputs(exclude_hidden=True).items():
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
        # Use the task class's declared output names rather than the current
        # (possibly empty, e.g. after a failed execution) task outputs, so
        # downstream nodes are always invalidated regardless of the outcome.
        if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
            for ewoksname in self.get_output_names(exclude_hidden=True):
                output = self._get_output_signal(ewoksname)
                self.send(output.name, invalid_data.INVALIDATION_DATA)
                # Note: perhaps `self.invalidate(output.name)` is equivalent
        else:
            for ewoksname in self.get_output_names(exclude_hidden=True):
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

    def execute_ewoks_task(
        self, log_missing_inputs: bool = True
    ) -> Optional[TaskFuture]:
        """
        Execute the Ewoks task and propagate downstream on completion.

        :param log_missing_inputs: Whether missing inputs should be logged.
        :return: The future of the submitted task, whose result is the task's
                 :class:`~ewokscore.variable.VariableContainer` of output
                 variables. `None` when the submission was dropped by
                 `SubmitPolicy.DROP_IF_BUSY`.
        """
        _logger.debug("%s: execute ewoks task (with propagation)", self)
        return self._execute_ewoks_task(
            propagate=True, log_missing_inputs=log_missing_inputs
        )

    def execute_ewoks_task_without_propagation(self) -> Optional[TaskFuture]:
        """
        Execute the Ewoks task without propagating outputs downstream.

        :return: The future of the submitted task, or `None` when the submission
                 was dropped by `SubmitPolicy.DROP_IF_BUSY`.
        """
        _logger.debug("%s: execute ewoks task (without propagation)", self)
        return self._execute_ewoks_task(propagate=False, log_missing_inputs=False)

    @property
    def task_executor(self) -> EwoksExecutor:
        """
        The executor that runs the Ewoks tasks.

        :return: The :class:`EwoksExecutor` instance.
        """
        return self.__executor

    @property
    def task_succeeded(self) -> Optional[bool]:
        """
        Whether the most recent task execution succeeded.

        :return: True if succeeded, False if failed, or None if never run.
        """
        return self.__last_task_succeeded

    @property
    def task_done(self) -> Optional[bool]:
        """
        Whether the most recent task execution finished (success or failure).

        :return: True/False or None if never run.
        """
        return self.__last_task_done

    @property
    def task_exception(self) -> Optional[Exception]:
        """
        Exception raised during the most recent task execution, if any.

        :return: Exception instance or None.
        """
        exc = self.__last_task_exception
        if exc is None:
            return None
        # task.execute() wraps run() exceptions as TaskExecutionError(...) from
        # the original; follow __cause__ to surface the exception the task
        # actually raised. Task construction failures (TaskInputError) have
        # no __cause__ and are returned as-is.
        return exc.__cause__ or exc

    def has_pending_task(self) -> bool:
        """
        Whether a task submission is outstanding, from submission until its
        completion callback (propagation + `progressBarFinished`) has run.

        Always False when tasks execute synchronously (`concurrency="sync"`): the
        completion callback has already run when the submission returns.

        :return: True while a submission is outstanding.
        """
        return bool(self.__propagate_by_future)

    def cancel_running_task(self) -> None:
        """Abort the currently running task."""
        warnings.warn(
            "'cancel_running_task' is deprecated since 6.0. Please cancel the task by calling the "
            " `cancel` method of the future provided during task submission.",
            DeprecationWarning,
        )
        if self.__current_task_future is not None:
            self.__current_task_future.abort()

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
            progress=self.__taskProgress,
        )
        return task_arguments

    def _output_changed(self) -> None:
        """
        Called when the Ewoks task execution finishes and outputs changed.

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

    def _execute_ewoks_task(
        self, propagate: bool, log_missing_inputs: bool
    ) -> Optional[TaskFuture]:
        """
        Submit the Ewoks task to the task executor.

        :param propagate: Whether to propagate outputs downstream after execution.
        :param log_missing_inputs: Whether to log missing input warnings.
        :return: TaskFuture or None when the execution request was rejected.
        """
        # Read back by `__on_submitted`. Submission always happens in the GUI
        # thread so a single slot is enough.
        self.__propagate_next = propagate
        return self.__executor.submit_task(
            self.ewokstaskclass, **self._get_task_arguments()
        )

    def __on_submitted(self, task_future: TaskFuture) -> None:
        """
        Remember whether the submitted task should propagate its outputs.

        The `submitted` signal is emitted before the task can start, which is
        why this cannot wait for `submit_task` to return: with synchronous
        execution (`concurrency="sync"`) the task already completed by then.

        :param task_future: The future of the submitted task.
        """
        self.__propagate_by_future[task_future] = self.__propagate_next

    def __on_started(self, task_future: TaskFuture) -> None:
        """
        Start the Orange progress bar when the task starts executing.

        :param task_future: The future of the started task.
        """
        self.__current_task_future = task_future
        self.progressBarInit()

    def __on_succeeded(self, task_future: TaskFuture) -> None:
        """
        Store the outputs of a successful task and propagate them downstream.

        :param task_future: The future of the successful task.
        """
        propagate = self.__propagate_by_future.get(task_future, False)
        self.__last_output_variables = task_future.result()
        self.__last_task_succeeded = True
        self.__last_task_done = True
        self.__last_task_exception = None
        # `propagate_downstream` must run before `progressBarFinished`: the
        # latter flips `signal_manager.is_active(node)` to False, which is
        # what `wait_widgets`-style polling relies on to know this widget is
        # done. Clearing it first would let such polling observe "not
        # active" before the outputs were actually sent downstream.
        # `has_pending_task()` must stay True until both of those have run,
        # for the same reason, so the future is only popped last.
        try:
            if propagate:
                self.propagate_downstream(succeeded=True)
        finally:
            self.progressBarFinished()
            self.__propagate_by_future.pop(task_future, None)
            self._output_changed()

    def __on_failed(self, task_future: TaskFuture) -> None:
        """
        Store the exception of a failed task and invalidate downstream nodes.

        :param task_future: The future of the failed task.
        """
        propagate = self.__propagate_by_future.get(task_future, False)
        self.__last_output_variables = None
        self.__last_task_succeeded = False
        self.__last_task_done = True
        self.__last_task_exception = task_future.exception()
        # See ordering note in `__on_succeeded`.
        try:
            if propagate:
                self.propagate_downstream(succeeded=False)
        finally:
            self.progressBarFinished()
            self.__propagate_by_future.pop(task_future, None)
            self._output_changed()
