"""
Orange widget base classes to execute Ewoks tasks
"""

import inspect
import logging
import warnings
from contextlib import contextmanager
from typing import Any, Optional
from AnyQt import QtWidgets

from ..orange_version import ORANGE_VERSION

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
    from oasys.widgets.widget import OWWidget
    from orangewidget.widget import WidgetMetaClass
    from orangewidget.settings import Setting

    OWBaseWidget = OWWidget
    summarize = None
    PartialSummary = None
    has_progress_bar = True
else:
    from orangewidget.widget import OWBaseWidget
    from orangewidget.settings import Setting
    from orangewidget.utils.signals import summarize
    from orangewidget.utils.signals import PartialSummary

    if ORANGE_VERSION == ORANGE_VERSION.latest_orange:
        from Orange.widgets.widget import OWWidget
        from Orange.widgets.widget import WidgetMetaClass

        has_progress_bar = True
    else:
        OWWidget = OWBaseWidget
        WidgetMetaClass = type(OWBaseWidget)
        has_progress_bar = False

from ewokscore.variable import Variable
from ewokscore.variable import value_from_transfer
from ewokscore import missing_data
from .progress import QProgress
from .taskexecutor import TaskExecutor
from .taskexecutor import ThreadedTaskExecutor
from .taskexecutor_queue import TaskExecutorQueue
from . import owsignals
from .events import scheme_ewoks_events
from . import invalid_data


_logger = logging.getLogger(__name__)


__all__ = [
    "OWEwoksWidgetNoThread",
    "OWEwoksWidgetOneThread",
    "OWEwoksWidgetOneThreadPerRun",
    "OWEwoksWidgetWithTaskStack",
    "ow_build_opts",
]


if summarize is not None:

    @summarize.register(Variable)
    def summarize_variable(var: Variable):
        if var.is_missing():
            dtype = var.value
        else:
            dtype = type(var.value).__name__
        desc = f"ewoks variable ({dtype})"
        return PartialSummary(desc, desc)

    @summarize.register(object)
    def summarize_object(value: object):
        return PartialSummary(str(type(value)), str(type(value)))


def prepare_OWEwoksWidgetclass(namespace, ewokstaskclass):
    """This needs to be called before signal and setting parsing"""
    # Add the Ewoks class as an attribute to the Orange widget class
    namespace["ewokstaskclass"] = ewokstaskclass

    # Make sure the values above are always the default setting values:
    # https://orange3.readthedocs.io/projects/orange-development/en/latest/tutorial-settings.html
    # schema_only=False: when a widget is removed, its settings are stored to be used
    #                    as defaults for future instances of this widget.
    # schema_only=True: setting defaults should not change. Future instances of this widget
    #                   have the default settings hard-coded in this function.
    schema_only = True

    # Add the settings as widget class attributes
    namespace["_ewoks_default_inputs"] = Setting(dict(), schema_only=schema_only)
    namespace["_ewoks_varinfo"] = Setting(dict(), schema_only=schema_only)
    namespace["_ewoks_execinfo"] = Setting(dict(), schema_only=schema_only)

    # Deprecated:
    namespace["default_inputs"] = Setting(dict(), schema_only=schema_only)

    # Add missing inputs and outputs as widget class attributes
    owsignals.validate_inputs(namespace)
    owsignals.validate_outputs(namespace)


class _OWEwoksWidgetMetaClass(WidgetMetaClass):
    def __new__(metacls, name, bases, attrs, ewokstaskclass=None, **kw):
        if ewokstaskclass:
            prepare_OWEwoksWidgetclass(attrs, ewokstaskclass)
        return super().__new__(metacls, name, bases, attrs, **kw)


# insure compatibility between old orange widget and new
# orangewidget.widget.WidgetMetaClass. This was before split of the two
# projects. Parameter name "openclass" is undefined on the old version
ow_build_opts = dict()
if "openclass" in inspect.signature(WidgetMetaClass).parameters:
    ow_build_opts["openclass"] = True


class OWEwoksBaseWidget(OWWidget, metaclass=_OWEwoksWidgetMetaClass, **ow_build_opts):
    """Base class for boiler plate code to interconnect ewoks and orange3"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dynamic_inputs = dict()
        self.__task_output_changed_callbacks = {self.task_output_changed}

    def _init_control_area(self):
        """The control area is used for task inputs."""
        layout = self._get_control_layout()
        trigger = QtWidgets.QPushButton("Trigger")
        layout.addWidget(trigger)
        trigger.released.connect(self.execute_ewoks_task)
        trigger = QtWidgets.QPushButton("Execute")
        layout.addWidget(trigger)
        trigger.released.connect(self.execute_ewoks_task_without_propagation)

    def _init_main_area(self):
        """The main area is used to display results."""
        self._get_main_layout()

    def _get_control_layout(self):
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
        if not self.want_main_area:
            raise RuntimeError(
                f"{type(self).__name__} must have class attribute `want_main_area = True`"
            )
        layout = self.mainArea.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout()
            self.mainArea.setLayout(layout)
        return layout

    def _get_task_arguments(self):
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
        return {
            "inputs": self.get_task_inputs(),
            "varinfo": self._ewoks_varinfo,
            "execinfo": execinfo,
            "node_id": node_id,
        }

    @classmethod
    def get_input_names(cls):
        return cls.ewokstaskclass.input_names()

    @classmethod
    def get_output_names(cls):
        return cls.ewokstaskclass.output_names()

    def _deprecated_default_inputs(self):
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

    def get_default_input_names(self) -> set:
        self._deprecated_default_inputs()
        return set(self._ewoks_default_inputs)

    def get_default_input_values(self) -> dict:
        self._deprecated_default_inputs()
        return {
            name: invalid_data.as_missing(value)
            for name, value in self._ewoks_default_inputs.items()
        }

    def update_default_inputs(self, **inputs) -> None:
        for name, value in inputs.items():
            if invalid_data.is_invalid_data(value):
                _logger.info("ewoks widget: remove default input %r", name)
                self._ewoks_default_inputs.pop(name, None)
            else:
                _logger.info("ewoks widget: set default input %r = %s", name, value)
                self._ewoks_default_inputs[name] = value

    def _receive_dynamic_input(self, name: str, value: Any):
        if invalid_data.is_invalid_data(value):
            _logger.info("ewoks widget: remove dynamic input %r", name)
            self.__dynamic_inputs.pop(name, None)
        else:
            _logger.info("ewoks widget: set dynamic input %r = %s", name, value)
            self.__dynamic_inputs[name] = value

    def get_dynamic_input_names(self) -> set:
        return set(self.__dynamic_inputs)

    def get_dynamic_input_values(self) -> dict:
        return {k: self._extract_value(v) for k, v in self.__dynamic_inputs.items()}

    def _extract_value(self, data) -> Any:
        return value_from_transfer(data, varinfo=self._ewoks_varinfo)

    def get_task_inputs(self) -> dict:
        """Default inputs overwritten by inputs from previous tasks"""
        inputs = self.get_default_input_values()
        inputs.update(self.__dynamic_inputs)
        return inputs

    def get_task_outputs(self):
        raise NotImplementedError("Base class")

    def get_task_output_values(self) -> dict:
        return {k: self._extract_value(v) for k, v in self.get_task_outputs().items()}

    def get_task_output_value(self, name) -> Any:
        adict = self.get_task_outputs()
        try:
            data = adict[name]
        except KeyError:
            return missing_data.MISSING_DATA
        return self._extract_value(data)

    def get_task_input_values(self) -> dict:
        return {k: self._extract_value(v) for k, v in self.get_task_inputs().items()}

    def get_task_input_value(self, name: str) -> Any:
        adict = self.get_task_inputs()
        try:
            data = adict[name]
        except KeyError:
            return missing_data.MISSING_DATA
        return self._extract_value(data)

    def _get_output_signal(self, ewoksname: str):
        if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
            for signal in self.outputs:
                if signal.name == ewoksname:
                    break
            else:
                signal = None
        else:
            signal = getattr(self.Outputs, ewoksname, None)
        if signal is None:
            raise RuntimeError(f"Output signal '{ewoksname}' does not exist")
        return signal

    def trigger_downstream(self) -> None:
        if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
            for ewoksname, var in self.get_task_outputs().items():
                ewoks_to_orange = owsignals.get_ewoks_to_orange_mapping(
                    type(self), "outputs"
                )
                orangename = ewoks_to_orange.get(ewoksname, ewoksname)
                if invalid_data.is_invalid_data(var.value):
                    self.send(
                        orangename, invalid_data.INVALIDATION_DATA
                    )  # or self.invalidate?
                else:
                    self.send(orangename, var)
        else:
            for ewoksname, var in self.get_task_outputs().items():
                channel = self._get_output_signal(ewoksname)
                if invalid_data.is_invalid_data(var.value):
                    channel.send(
                        invalid_data.INVALIDATION_DATA
                    )  # or channel.invalidate?
                else:
                    channel.send(var)

    def _output_changed(self) -> None:
        for cb in self.__task_output_changed_callbacks:
            cb()

    @property
    def task_output_changed_callbacks(self) -> set:
        return self.__task_output_changed_callbacks

    def task_output_changed(self) -> None:
        """Called when the task output has changed"""
        pass

    def clear_downstream(self) -> None:
        if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
            for name in self.get_task_outputs():
                self.send(name, invalid_data.INVALIDATION_DATA)  # or self.invalidate?
        else:
            for name in self.get_task_outputs():
                channel = self._get_output_signal(name)
                channel.send(invalid_data.INVALIDATION_DATA)  # or channel.invalidate?

    def propagate_downstream(self, succeeded: Optional[bool] = None) -> None:
        if succeeded is None:
            succeeded = self.task_succeeded
        if succeeded:
            _logger.debug("%s: trigger downstream", self)
            self.trigger_downstream()
        else:
            _logger.debug("%s: clear downstream", self)
            self.clear_downstream()

    def handleNewSignals(self) -> None:
        """Invoked by the workflow signal propagation manager after all
        signals handlers have been called.
        """
        self.execute_ewoks_task()

    def execute_ewoks_task(self) -> None:
        _logger.debug("%s: execute ewoks task (with propagation)", self)
        self._execute_ewoks_task(propagate=True)

    def execute_ewoks_task_without_propagation(self) -> None:
        _logger.debug("%s: execute ewoks task (without propagation)", self)
        self._execute_ewoks_task(propagate=False)

    def _execute_ewoks_task(self, propagate: bool) -> None:
        raise NotImplementedError("Base class")

    @property
    def task_succeeded(self) -> Optional[bool]:
        raise NotImplementedError("Base class")

    @property
    def task_done(self) -> Optional[bool]:
        raise NotImplementedError("Base class")


def is_orange_widget_class(widget_class):
    return issubclass(widget_class, OWBaseWidget)


def is_ewoks_widget_class(widget_class):
    return issubclass(widget_class, OWEwoksBaseWidget)


def is_native_widget_class(widget_class):
    return is_orange_widget_class(widget_class) and not is_ewoks_widget_class(
        widget_class
    )


def is_orange_widget(widget):
    return isinstance(widget, OWBaseWidget)


def is_ewoks_widget(widget):
    return isinstance(widget, OWEwoksBaseWidget)


def is_native_widget(widget_class):
    return is_orange_widget(widget_class) and not is_ewoks_widget(widget_class)


class OWEwoksWidgetNoThread(OWEwoksBaseWidget, **ow_build_opts):
    """Widget which will execute_ewoks_task the ewokscore.Task directly"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__task_executor = TaskExecutor(self.ewokstaskclass)

    def _execute_ewoks_task(self, propagate: bool):
        self.__task_executor.create_task(**self._get_task_arguments())
        try:
            self.__task_executor.execute_task()
        except Exception:
            _logger.error("task failed", exc_info=True)
        finally:
            self._output_changed()
        if propagate:
            self.propagate_downstream()

    @property
    def task_succeeded(self) -> Optional[bool]:
        return self.__task_executor.succeeded

    @property
    def task_done(self) -> Optional[bool]:
        return self.__task_executor.done

    def get_task_outputs(self):
        return self.__task_executor.output_variables


class _OWEwoksThreadedBaseWidget(OWEwoksBaseWidget, **ow_build_opts):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if has_progress_bar:
            self.__taskProgress = QProgress()
            self.__taskProgress.sigProgressChanged.connect(self.progressBarSet)
        else:
            self.__taskProgress = None

    def onDeleteWidget(self):
        if has_progress_bar:
            self.__taskProgress.sigProgressChanged.disconnect(self.progressBarSet)
        self._cleanup_task_executor()
        super().onDeleteWidget()

    def _cleanup_task_executor(self):
        raise NotImplementedError("Base class")

    @contextmanager
    def _ewoks_task_start_context(self):
        try:
            self.__ewoks_task_init()
            yield
        except Exception:
            self.__ewoks_task_finished()
            raise

    @contextmanager
    def _ewoks_task_finished_context(self):
        try:
            yield
        finally:
            self.__ewoks_task_finished()

    def __ewoks_task_init(self):
        if has_progress_bar:
            self.progressBarInit()

    def __ewoks_task_finished(self):
        if has_progress_bar:
            self.progressBarFinished()
        self._output_changed()

    def _get_task_arguments(self):
        adict = super()._get_task_arguments()
        adict["progress"] = self.__taskProgress
        return adict


class OWEwoksWidgetOneThread(_OWEwoksThreadedBaseWidget, **ow_build_opts):
    """
    All the processing is done on one thread.
    If a processing is requested when the thread is already running then
    it is refused.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__task_executor = ThreadedTaskExecutor(ewokstaskclass=self.ewokstaskclass)
        self.__task_executor.finished.connect(self._ewoks_task_finished_callback)
        self.__propagate = None

    def _execute_ewoks_task(self, propagate: bool):
        if self.__task_executor.isRunning():
            _logger.error("A processing is already ongoing")
            return
        else:
            self.__task_executor.create_task(**self._get_task_arguments())
            if self.__task_executor.has_task:
                with self._ewoks_task_start_context():
                    self.__propagate = propagate
                    self.__task_executor.start()

    @property
    def task_succeeded(self) -> Optional[bool]:
        return self.__task_executor.succeeded

    @property
    def task_done(self) -> Optional[bool]:
        return self.__task_executor.done

    def get_task_outputs(self):
        return self.__task_executor.output_variables

    def _ewoks_task_finished_callback(self):
        with self._ewoks_task_finished_context():
            if self.__propagate:
                self.propagate_downstream()

    def _cleanup_task_executor(self):
        self.__task_executor.finished.disconnect(self._ewoks_task_finished_callback)
        self.__task_executor.stop()
        self.__task_executor = None


class OWEwoksWidgetOneThreadPerRun(_OWEwoksThreadedBaseWidget, **ow_build_opts):
    """
    Each time a task processing is requested this will create a new thread
    to do the processing.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__task_executors = dict()
        self.__last_output_variables = dict()
        self.__last_task_succeeded = None
        self.__last_task_done = None

    def _execute_ewoks_task(self, propagate: bool):
        task_executor = ThreadedTaskExecutor(ewokstaskclass=self.ewokstaskclass)
        task_executor.create_task(**self._get_task_arguments())
        if not task_executor.has_task:
            return
        with self.__init_task_executor(task_executor, propagate):
            with self._ewoks_task_start_context():
                task_executor.start()

    @contextmanager
    def __init_task_executor(self, task_executor, propagate: bool):
        self.__disconnect_all_task_executors()
        task_executor.finished.connect(self._ewoks_task_finished_callback)
        self.__add_task_executor(task_executor, propagate)
        try:
            yield
        except Exception:
            task_executor.finished.disconnect(self._ewoks_task_finished_callback)
            self.__remove_task_executor(task_executor)
            raise

    def __disconnect_all_task_executors(self):
        for task_executor, _ in self.__task_executors:
            try:
                task_executor.finished.disconnect(self._ewoks_task_finished_callback)
            except KeyError:
                pass

    def _ewoks_task_finished_callback(self):
        with self._ewoks_task_finished_context():
            task_executor = None
            try:
                task_executor = self.sender()
                self.__last_output_variables = task_executor.output_variables
                self.__last_task_succeeded = task_executor.succeeded
                self.__last_task_done = task_executor.done
                if self.__is_task_executor_propagated(task_executor):
                    self.propagate_downstream(succeeded=task_executor.succeeded)
            finally:
                self.__remove_task_executor(task_executor)

    def _cleanup_task_executor(self):
        self.__disconnect_all_task_executors()
        for task_executor, _ in self.__task_executors:
            task_executor.quit()
        self.__task_executors.clear()

    def __add_task_executor(self, task_executor, propagate: bool):
        self.__task_executors[id(task_executor)] = task_executor, propagate

    def __remove_task_executor(self, task_executor):
        self.__task_executors.pop(id(task_executor), None)

    def __is_task_executor_propagated(self, task_executor) -> bool:
        return self.__task_executors.get(id(task_executor), (None, False))[1]

    @property
    def task_succeeded(self) -> Optional[bool]:
        return self.__last_task_succeeded

    @property
    def task_done(self) -> Optional[bool]:
        return self.__last_task_done

    def get_task_outputs(self):
        return self.__last_output_variables


class OWEwoksWidgetWithTaskStack(_OWEwoksThreadedBaseWidget, **ow_build_opts):
    """
    Each time a task processing is requested add it to the FIFO stack.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__task_executor_queue = TaskExecutorQueue(
            ewokstaskclass=self.ewokstaskclass
        )
        self.__last_output_variables = dict()
        self.__last_task_succeeded = None
        self.__last_task_done = None

    @property
    def task_executor_queue(self):
        return self.__task_executor_queue

    def _execute_ewoks_task(self, propagate):
        def callback():
            self._ewoks_task_finished_callback(propagate)

        with self._ewoks_task_start_context():
            self.__task_executor_queue.add(
                _callbacks=(callback,),
                **self._get_task_arguments(),
            )

    @property
    def task_succeeded(self) -> Optional[bool]:
        return self.__last_task_succeeded

    @property
    def task_done(self) -> Optional[bool]:
        return self.__last_task_done

    def get_task_outputs(self):
        return self.__last_output_variables

    def _cleanup_task_executor(self):
        self.__task_executor_queue.stop()
        self.__task_executor_queue = None

    def _ewoks_task_finished_callback(self, propagate: bool):
        with self._ewoks_task_finished_context():
            task_executor = self.sender()
            self.__last_output_variables = task_executor.output_variables
            self.__last_task_succeeded = task_executor.succeeded
            self.__last_task_done = task_executor.done
            if propagate:
                self.propagate_downstream()
