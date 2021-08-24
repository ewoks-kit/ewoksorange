"""
Orange widget base classes to execute Ewoks tasks
"""
import inspect
import logging
from contextlib import contextmanager

from Orange.widgets.widget import OWWidget, WidgetMetaClass
from Orange.widgets.settings import Setting

try:
    from orangewidget.utils.signals import summarize, PartialSummary
except ImportError:
    summarize = None

from ewokscore.variable import Variable
from ewokscore.hashing import UniversalHashable
from ewokscore.hashing import MissingData
from .progress import QProgress
from .taskexecutor import TaskExecutor
from .taskexecutor import ThreadedTaskExecutor
from .taskexecutor_queue import TaskExecutorQueue
from .ewoksowsignals import validate_inputs
from .ewoksowsignals import validate_outputs


_logger = logging.getLogger(__name__)


__all__ = [
    "OWEwoksWidgetNoThread",
    "OWEwoksWidgetOneThread",
    "OWEwoksWidgetOneThreadPerRun",
    "OWEwoksWidgetWithTaskStack",
]


MISSING_DATA = UniversalHashable.MISSING_DATA
INVALIDATION_DATA = None  # This means we cannot use `None` as a value


if summarize is not None:

    @summarize.register(Variable)
    def summarize_variable(var: Variable):
        if var.value is MISSING_DATA:
            dtype = MISSING_DATA
        else:
            dtype = type(var.value).__name__
        desc = f"ewoks variable ({dtype})"
        return PartialSummary(desc, desc)

    @summarize.register(object)
    def summarize_object(value: object):
        return PartialSummary(str(type(value)), str(type(value)))


def prepare_OWEwoksWidgetclass(namespace, ewokstaskclass):
    """This needs to be called before signal and setting parsing"""
    namespace["ewokstaskclass"] = ewokstaskclass
    namespace["static_input"] = Setting(
        {name: INVALIDATION_DATA for name in ewokstaskclass.input_names()}
    )
    namespace["varinfo"] = Setting({"root_uri": ""})
    namespace["static_input"].schema_only = True
    namespace["varinfo"].schema_only = True
    validate_inputs(namespace)
    validate_outputs(namespace)


class _OWEwoksWidgetMetaClass(WidgetMetaClass):
    def __new__(metacls, name, bases, attrs, ewokstaskclass=None, **kw):
        if ewokstaskclass:
            prepare_OWEwoksWidgetclass(attrs, ewokstaskclass)
        return super().__new__(metacls, name, bases, attrs, **kw)


# insure compatibility between old orange widget and new
# orangewidget.widget.WidgetMetaClass. This was before split of the two
# projects. Parameter name "openclass" is undefined on the old version
ow_build_opts = {}
if "openclass" in inspect.signature(WidgetMetaClass).parameters:
    ow_build_opts["openclass"] = True


class _OWEwoksBaseWidget(OWWidget, metaclass=_OWEwoksWidgetMetaClass, **ow_build_opts):
    """
    Base class to handle boiler plate code to interconnect ewoks and
    orange3
    """

    MISSING_DATA = MISSING_DATA

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dynamic_inputs = dict()
        self.ewoks_output_callbacks = tuple()

    @classmethod
    def input_names(cls):
        return cls.ewokstaskclass.input_names()

    @classmethod
    def output_names(cls):
        return cls.ewokstaskclass.output_names()

    def _getTaskArguments(self):
        inputs = self.defined_static_input_values
        inputs.update(self.__dynamic_inputs)
        return {"inputs": inputs, "varinfo": self.varinfo}

    @staticmethod
    def _get_value(value):
        if isinstance(value, Variable):
            return value.value
        if isinstance(value, MissingData):
            # `Setting` seems to make a copy of MISSING_DATA
            return MISSING_DATA
        return value

    @property
    def defined_static_input_values(self):
        # Warning: do not use static_input directly because it
        #          messes up MISSING_DATA
        return {
            k: self._get_value(v)
            for k, v in self.static_input.items()
            if v is not INVALIDATION_DATA
        }

    @property
    def static_input_values(self):
        values = {name: MISSING_DATA for name in self.input_names()}
        values.update(self.defined_static_input_values)
        return values

    @property
    def dynamic_input_values(self):
        return {k: self._get_value(v) for k, v in self.__dynamic_inputs.items()}

    def receiveDynamicInputs(self, name, value):
        if value is INVALIDATION_DATA:
            self.__dynamic_inputs.pop(name, INVALIDATION_DATA)
        else:
            self.__dynamic_inputs[name] = value

    def trigger_downstream(self):
        for name, var in self.output_variables.items():
            channel = getattr(self.Outputs, name)
            if var.value is MISSING_DATA:
                channel.send(INVALIDATION_DATA)  # or channel.invalidate?
            else:
                channel.send(var)
        for cb in self.ewoks_output_callbacks:
            cb(self.output_variables)

    def clear_downstream(self):
        for name in self.output_variables:
            channel = getattr(self.Outputs, name)
            channel.send(INVALIDATION_DATA)  # or channel.invalidate?

    def staticInputHasChanged(self):
        """Needs to be called when static inputs have changed"""
        self.executeEwoksTask()

    def handleNewSignals(self):
        """Invoked by the workflow signal propagation manager after all
        signals handlers have been called.
        """
        self.executeEwoksTask()

    def executeEwoksTask(self):
        raise NotImplementedError("Base class")

    @property
    def output_variables(self):
        raise NotImplementedError("Base class")

    @property
    def output_values(self):
        return {name: var.value for name, var in self.output_variables.items()}


class OWEwoksWidgetNoThread(_OWEwoksBaseWidget, **ow_build_opts):
    """Widget which will executeEwoksTask the ewokscore.Task directly"""

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.__taskExecutor = TaskExecutor(self.ewokstaskclass)

    def executeEwoksTask(self):
        self.__taskExecutor.create_task(**self._getTaskArguments())
        try:
            self.__taskExecutor.execute_task()
        except Exception:
            self.clear_downstream()
            raise
        if self.__taskExecutor.succeeded:
            self.trigger_downstream()
        else:
            self.clear_downstream()

    @property
    def output_variables(self):
        return self.__taskExecutor.output_variables


class _OWEwoksThreadedBaseWidget(_OWEwoksBaseWidget, **ow_build_opts):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.__taskProgress = QProgress()
        self.__taskProgress.sigProgressChanged.connect(self.progressBarSet)

    def onDeleteWidget(self):
        self.__taskProgress.sigProgressChanged.disconnect(self.progressBarSet)
        self._cleanupTaskExecutor()
        super().onDeleteWidget()

    def _cleanupTaskExecutor(self):
        raise NotImplementedError("Base class")

    @contextmanager
    def _ewoksTaskStartContext(self):
        try:
            self.__ewoksTaskInit()
            yield
        except Exception:
            self.__ewoksTaskFinished()
            raise

    @contextmanager
    def _ewoksTaskFinishedContext(self):
        try:
            yield
        finally:
            self.__ewoksTaskFinished()

    def __ewoksTaskInit(self):
        self.progressBarInit()

    def __ewoksTaskFinished(self):
        self.progressBarFinished()

    def _getTaskArguments(self):
        adict = super()._getTaskArguments()
        adict["progress"] = self.__taskProgress
        return adict


class OWEwoksWidgetOneThread(_OWEwoksThreadedBaseWidget, **ow_build_opts):
    """
    All the processing is done on one thread.
    If a processing is requested when the thread is already running then
    it is refused.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.__taskExecutor = ThreadedTaskExecutor(ewokstaskclass=self.ewokstaskclass)
        self.__taskExecutor.finished.connect(self._ewoksTaskFinishedCallback)

    def executeEwoksTask(self):
        if self.__taskExecutor.isRunning():
            _logger.error("A processing is already on going")
            return
        else:
            self.__taskExecutor.create_task(**self._getTaskArguments())
            if self.__taskExecutor.is_ready_to_execute:
                with self._ewoksTaskStartContext():
                    self.__taskExecutor.start()

    @property
    def output_variables(self):
        return self.__taskExecutor.output_variables

    def _ewoksTaskFinishedCallback(self):
        with self._ewoksTaskFinishedContext():
            if self.__taskExecutor.succeeded:
                self.trigger_downstream()
            else:
                self.clear_downstream()

    def _cleanupTaskExecutor(self):
        self.__taskExecutor.finished.disconnect(self._ewoksTaskFinishedCallback)
        self.__taskExecutor.stop()
        self.__taskExecutor = None


class OWEwoksWidgetOneThreadPerRun(_OWEwoksThreadedBaseWidget, **ow_build_opts):
    """
    Each time a task processing is requested this will create a new thread
    to do the processing.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__taskExecutors = list()
        self.__last_output_variables = dict()

    def executeEwoksTask(self):
        taskExecutor = ThreadedTaskExecutor(ewokstaskclass=self.ewokstaskclass)
        taskExecutor.create_task(**self._getTaskArguments())
        if not taskExecutor.is_ready_to_execute:
            return
        with self.__addTaskExecutor(taskExecutor):
            with self._ewoksTaskStartContext():
                taskExecutor.start()

    @contextmanager
    def __addTaskExecutor(self, taskExecutor):
        self.__disconnectAllTaskExecutors()
        taskExecutor.finished.connect(self._ewoksTaskFinishedCallback)
        self.__taskExecutors.append(taskExecutor)
        try:
            yield
        except Exception:
            taskExecutor.finished.disconnect(self._ewoksTaskFinishedCallback)
            self.__taskExecutors.remove(taskExecutor)
            raise

    def __disconnectAllTaskExecutors(self):
        for taskExecutor in self.__taskExecutors:
            try:
                taskExecutor.finished.disconnect(self._ewoksTaskFinishedCallback)
            except KeyError:
                pass

    def _ewoksTaskFinishedCallback(self):
        with self._ewoksTaskFinishedContext():
            try:
                taskExecutor = self.sender()
                self.__last_output_variables = taskExecutor.output_variables
                if taskExecutor.succeeded:
                    self.trigger_downstream()
                else:
                    self.clear_downstream()
            finally:
                if taskExecutor in self.__taskExecutors:
                    self.__taskExecutors.remove(taskExecutor)

    def _cleanupTaskExecutor(self):
        self.__disconnectAllTaskExecutors()
        for taskExecutor in self.__taskExecutors:
            taskExecutor.quit()
        self.__taskExecutors.clear()

    @property
    def output_variables(self):
        return self.__last_output_variables


class OWEwoksWidgetWithTaskStack(_OWEwoksThreadedBaseWidget, **ow_build_opts):
    """
    Each time a task processing is requested add it to the FIFO stack.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__taskExecutorQueue = TaskExecutorQueue(ewokstaskclass=self.ewokstaskclass)
        self.__last_output_variables = dict()

    def executeEwoksTask(self):
        with self._ewoksTaskStartContext():
            self.__taskExecutorQueue.add(
                _callbacks=(self._ewoksTaskFinishedCallback,),
                **self._getTaskArguments(),
            )

    @property
    def output_variables(self):
        return self.__last_output_variables

    def _cleanupTaskExecutor(self):
        self.__taskExecutorQueue.stop()
        self.__taskExecutorQueue = None

    def _ewoksTaskFinishedCallback(self):
        with self._ewoksTaskFinishedContext():
            taskExecutor = self.sender()
            self.__last_output_variables = taskExecutor.output_variables
            if taskExecutor.succeeded:
                self.trigger_downstream()
            else:
                self.clear_downstream()
