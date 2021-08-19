"""
contains Orange widget that can create direct connection with ewoks
"""
from contextlib import contextmanager
from Orange.widgets.widget import OWWidget, WidgetMetaClass
from Orange.widgets.widget import Input, Output
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
import inspect
import logging

_logger = logging.getLogger(__name__)


__all__ = [
    "OWEwoksWidgetNoThread",
    "OWEwoksWidgetOneThread",
    "OWEwoksWidgetOneThreadPerRun",
    "OWEwoksWidgetWithTaskStack",
]


MISSING_DATA = UniversalHashable.MISSING_DATA


def input_setter(name):
    def setter(self, var):
        self.set_input(name, var)

    return setter


if summarize is not None:

    @summarize.register(Variable)
    def summarize_variable(var: Variable):
        if var.value is MISSING_DATA:
            dtype = MISSING_DATA
        else:
            dtype = type(var.value).__name__
        desc = f"ewoks variable ({dtype})"
        return PartialSummary(desc, desc)


def prepare_OWEwoksWidgetclass(
    attr, ewokstaskclass=None, inputnamemap=None, outputnamemap=None
):
    """This needs to be called before signal and setting parsing"""
    if ewokstaskclass is None:
        return

    class Inputs:
        pass

    class Outputs:
        pass

    attr["ewokstaskclass"] = ewokstaskclass
    attr["Inputs"] = Inputs
    attr["Outputs"] = Outputs
    attr["static_input"] = Setting(
        {name: None for name in ewokstaskclass.input_names()}
    )
    attr["varinfo"] = Setting({"root_uri": ""})
    attr["static_input"].schema_only = True
    attr["varinfo"].schema_only = True

    if inputnamemap is None:
        inputnamemap = {}
    if outputnamemap is None:
        outputnamemap = {}

    for name in ewokstaskclass.input_names():
        inpt = Input(inputnamemap.get(name, name), Variable)
        setattr(Inputs, name, inpt)
        funcname = "_setter_" + name
        method = input_setter(name)
        method.__name__ = funcname
        attr[funcname] = inpt(method)

    for name in ewokstaskclass.output_names():
        output = Output(outputnamemap.get(name, name), Variable)
        setattr(Outputs, name, output)


class _OWEwoksWidgetMetaClass(WidgetMetaClass):
    def __new__(
        metacls,
        name,
        bases,
        attr,
        ewokstaskclass=None,
        inputnamemap=None,
        outputnamemap=None,
        **kw,
    ):
        prepare_OWEwoksWidgetclass(
            attr,
            ewokstaskclass=ewokstaskclass,
            inputnamemap=inputnamemap,
            outputnamemap=outputnamemap,
        )
        return super().__new__(metacls, name, bases, attr, **kw)


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

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.__dynamic_inputs = dict()

    @classmethod
    def input_names(cls):
        return cls.ewokstaskclass.input_names()

    @classmethod
    def output_names(cls):
        return cls.ewokstaskclass.output_names()

    @property
    def _task_arguments(self):
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
        return {k: self._get_value(v) for k, v in self.static_input.items()}

    @property
    def static_input_values(self):
        values = {name: MISSING_DATA for name in self.input_names()}
        values.update(self.defined_static_input_values)
        return values

    @property
    def dynamic_input_values(self):
        return {k: self._get_value(v) for k, v in self.__dynamic_inputs.items()}

    def set_input(self, name, var):
        if var is None:
            self.__dynamic_inputs.pop(name, None)
        else:
            if not isinstance(var, Variable):
                raise TypeError(
                    "{} is invalid. Expected to be an "
                    "instance of {}".format(var, Variable)
                )
            self.__dynamic_inputs[name] = var

    def trigger_downstream(self):
        for name, var in self.output_variables.items():
            channel = getattr(self.Outputs, name)
            if var.value is MISSING_DATA:
                channel.send(None)  # or channel.invalidate?
            else:
                channel.send(var)

    def clear_downstream(self):
        for name in self.output_variables:
            channel = getattr(self.Outputs, name)
            channel.send(None)  # or channel.invalidate?

    def staticInputHasChanged(self):
        """Needs to be called when static inputs have changed"""
        self.execute_task()

    def handleNewSignals(self):
        """Invoked by the workflow signal propagation manager after all
        signals handlers have been called.
        """
        self.execute_task()

    def execute_task(self):
        raise NotImplementedError("Base class")

    @property
    def output_variables(self):
        raise NotImplementedError("Base class")

    @property
    def output_values(self):
        return {name: var.value for name, var in self.output_variables.items()}


class OWEwoksWidgetNoThread(_OWEwoksBaseWidget, **ow_build_opts):
    """Widget which will execute_task the ewokscore.Task directly"""

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.__taskExecutor = TaskExecutor(self.ewokstaskclass)

    def execute_task(self):
        self.__taskExecutor.create_task(**self._task_arguments)
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
    def onDeleteWidget(self):
        self._cleanupTaskExecutor()
        super().onDeleteWidget()

    def _cleanupTaskExecutor(self):
        raise NotImplementedError("Base class")


class _OWEwoksThreadedBaseWidgetWithProgress(
    _OWEwoksThreadedBaseWidget, **ow_build_opts
):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self._taskProgress = QProgress()
        self._taskProgress.sigProgressChanged.connect(self.progressBarSet)

    def onDeleteWidget(self):
        self._taskProgress.sigProgressChanged.disconnect(self.progressBarSet)
        super().onDeleteWidget()

    @contextmanager
    def progressBarInitSafe(self):
        self.progressBarInit()
        try:
            yield
        except Exception:
            self.progressBarFinished()
            raise


class OWEwoksWidgetOneThread(_OWEwoksThreadedBaseWidgetWithProgress, **ow_build_opts):
    """
    All the processing is done on one thread.
    If a processing is requested when the thread is already running then
    it is refused.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.__taskExecutor = ThreadedTaskExecutor(ewokstaskclass=self.ewokstaskclass)
        self.__taskExecutor.finished.connect(self._taskFinishedCallback)

    def execute_task(self):
        if self.__taskExecutor.isRunning():
            _logger.error("A processing is already on going")
            return
        else:
            self.__taskExecutor.create_task(
                progress=self._taskProgress, **self._task_arguments
            )
            if self.__taskExecutor.is_ready_to_execute:
                with self.progressBarInitSafe():
                    self.__taskExecutor.start()

    @property
    def output_variables(self):
        return self.__taskExecutor.output_variables

    def _taskFinishedCallback(self):
        self.progressBarFinished()
        self.trigger_downstream()

    def _cleanupTaskExecutor(self):
        self.__taskExecutor.finished.disconnect(self._taskFinishedCallback)
        if self.__taskExecutor.isRunning():
            self.__taskExecutor.quit()
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

    def execute_task(self):
        taskExecutor = ThreadedTaskExecutor(ewokstaskclass=self.ewokstaskclass)
        taskExecutor.create_task(**self._task_arguments)
        if not taskExecutor.is_ready_to_execute:
            return
        taskExecutor.finished.connect(self._taskFinishedCallback)
        self.__taskExecutors.append(taskExecutor)
        taskExecutor.start()

    def _taskFinishedCallback(self):
        taskExecutor = self.sender()
        self.__last_output_variables = taskExecutor.output_variables
        if taskExecutor in self.__taskExecutors:
            self.__taskExecutors.remove(taskExecutor)
        self.trigger_downstream()

    def _cleanupTaskExecutor(self):
        for taskExecutor in self.__taskExecutors:
            taskExecutor.finished.disconnect(self._taskFinishedCallback)
            taskExecutor.quit()
        self.__taskExecutors.clear()

    @property
    def output_variables(self):
        return self.__last_output_variables


class OWEwoksWidgetWithTaskStack(
    _OWEwoksThreadedBaseWidgetWithProgress, **ow_build_opts
):
    """
    Each time a task processing is requested add it to the FIFO stack.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__taskExecutorQueue = TaskExecutorQueue(ewokstaskclass=self.ewokstaskclass)
        self.__last_output_variables = dict()

    def execute_task(self):
        with self.progressBarInitSafe():
            self.__taskExecutorQueue.add(
                progress=self._taskProgress,
                _callbacks=(self._taskFinishedCallback,),
                **self._task_arguments,
            )

    @property
    def output_variables(self):
        return self.__last_output_variables

    def _cleanupTaskExecutor(self):
        self.__taskExecutorQueue.stop()
        self.__taskExecutorQueue = None

    def _taskFinishedCallback(self):
        self.progressBarFinished()
        taskExecutor = self.sender()
        self.__last_output_variables = taskExecutor.output_variables
        self.trigger_downstream()
