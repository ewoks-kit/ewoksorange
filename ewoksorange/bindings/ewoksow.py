"""
contains Orange widget that can create direct connection with ewoks
"""
from Orange.widgets.widget import OWWidget, WidgetMetaClass
from Orange.widgets.widget import Input, Output
from Orange.widgets.settings import Setting
from Orange.widgets import gui
from ewokscore.variable import Variable
from ewokscore.task import TaskInputError
from ewokscore.hashing import UniversalHashable
from ewokscore.hashing import MissingData
from .progress import QProgress
from .taskexecutor import _TaskExecutor, _ProcessingThread
from .stack import FIFOTaskStack
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
        **kw
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


class _OWEwoksBaseWidget(
    OWWidget, _TaskExecutor, metaclass=_OWEwoksWidgetMetaClass, **ow_build_opts
):
    """
    Base class to handle boiler plate code to interconnect ewoks and
    orange3
    """

    MISSING_DATA = MISSING_DATA

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._dynamic_inputs = dict()
        self._output_variables = dict()

    @classmethod
    def input_names(cls):
        return cls.ewokstaskclass.input_names()

    @classmethod
    def output_names(cls):
        return cls.ewokstaskclass.output_names()

    @property
    def _all_inputs(self):
        inputs = self.static_input_values
        inputs.update(self._dynamic_inputs)
        return inputs

    @staticmethod
    def _get_value(value):
        if isinstance(value, Variable):
            return value.value
        if isinstance(value, MissingData):
            # `Setting` seems to make a copy of MISSING_DATA
            return MISSING_DATA
        return value

    @property
    def static_input_values(self):
        # Warning: do not use static_input directly because it
        #          messes up MISSING_DATA
        return {k: self._get_value(v) for k, v in self.static_input.items()}

    @property
    def dynamic_input_values(self):
        return {k: self._get_value(v) for k, v in self._dynamic_inputs.items()}

    def set_input(self, name, var):
        if var is None:
            self._dynamic_inputs.pop(name, None)
        else:
            if not isinstance(var, Variable):
                raise TypeError(
                    "{} is invalid. Expected to be an "
                    "instance of {}".format(var, Variable)
                )
            self._dynamic_inputs[name] = var

    def trigger_downstream(self):
        for name, var in self._output_variables.items():
            channel = getattr(self.Outputs, name)
            if var.value is MISSING_DATA:
                channel.send(None)  # or channel.invalidate?
            else:
                channel.send(var)

    def clear_downstream(self):
        for name in self._output_variables:
            channel = getattr(self.Outputs, name)
            channel.send(None)  # or channel.invalidate?

    def run(self):
        raise NotImplementedError("Base class")


class OWEwoksWidgetNoThread(_OWEwoksBaseWidget, _TaskExecutor):
    """Widget which will run the ewokscore.Task directly"""

    def changeStaticInput(self):
        self.handleNewSignals()

    def handleNewSignals(self):
        # update task inputs
        self.inputs = self._all_inputs
        self.run()

    def run(self):
        try:
            self.create_task()
        except TaskInputError:
            self.clear_downstream()
            return
        if not self.task.is_ready_to_execute:
            self.clear_downstream()
            return
        try:
            _TaskExecutor.run(self)
        except TaskInputError:
            self.clear_downstream()
            return
        except Exception:
            self.clear_downstream()
            raise
        self.trigger_downstream()


class OWEwoksWidgetOneThread(_OWEwoksBaseWidget):
    """
    All the processing is done on one thread.
    If a processing is requested when the thread is already running then
    it is refused.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self._orangeProgress = gui.ProgressBar(self, 100)
        self._taskProgress = QProgress()
        self._processingThread = _ProcessingThread(
            taskprogress=self._taskProgress, ewokstaskclass=self.ewokstaskclass
        )
        # connect signal / slot
        self._taskProgress.sigProgressChanged.connect(self._setProgressValue)
        self._processingThread.finished.connect(self._processingFinished)

    def run(self):
        # TODO: handle empty inputs. When a link is removed by orange the
        # value of the input is set to None and this trigger handleNewSignals
        if self._processingThread.isRunning():
            _logger.error("A processing is already on going")
            return
        else:
            self._setProgressValue(0)
            self._processingThread.init(varinfo=self.varinfo, inputs=self._all_inputs)
            self._processingThread.start()

    def _setProgressValue(self, value):
        self._orangeProgress.widget.progressBarSet(value)

    def _processingFinished(self):
        self._output_variables = self._processingThread.output_variables
        self.trigger_downstream()

    def changeStaticInput(self):
        self.handleNewSignals()

    def handleNewSignals(self):
        self.run()

    def getProcessingThread(self):
        return self._processingThread

    def close(self):
        self._taskProgress.sigProgressChanged.disconnect(self._setProgressValue)
        self._processingThread.finished.disconnect(self._processingFinished)
        if self._processingThread.isRunning():
            self._processingThread.quit()
        self._processingThread = None
        super().close()


class OWEwoksWidgetOneThreadPerRun(_OWEwoksBaseWidget):
    """
    Each time a task processing is requested this will create a new thread
    to do the processing.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._threads = list()
        # allows to keep trace of threads an insure there won't be removed by
        # Qt until they are no more used

    def run(self):
        processingThread = _ProcessingThread(
            taskprogress=None, ewokstaskclass=self.ewokstaskclass
        )
        processingThread.init(varinfo=self.varinfo, inputs=self._all_inputs)
        processingThread.finished.connect(self._processingFinished)
        self._threads.append(processingThread)
        processingThread.start()

    def _processingFinished(self):
        thread = self.sender()
        self._output_variables = thread.output_variables
        if thread in self._threads:
            self._threads.remove(thread)
        self.trigger_downstream()

    def changeStaticInput(self):
        self.handleNewSignals()

    def handleNewSignals(self):
        self.run()

    def close(self):
        for thread in self._threads:
            thread.finished.disconnect(self._processingFinished)
            thread.quit()
        self._threads.clear()
        super().close()


class OWEwoksWidgetWithTaskStack(_OWEwoksBaseWidget):
    """
    Each time a task processing is requested add it to the FIFO stack.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._taskProgress = QProgress()
        self._orangeProgress = gui.ProgressBar(self, 100)
        self._stack = FIFOTaskStack(
            ewokstaskclass=self.ewokstaskclass, taskprogress=self._taskProgress
        )
        # connect signal / slot
        self._taskProgress.sigProgressChanged.connect(self._setProgressValue)

    def run(self):
        self._stack.add(
            varinfo=self.varinfo,
            inputs=self._all_inputs,
            callbacks=(self._processingFinished,),
        )

    def close(self):
        self._stack.stop()
        super().close()

    def _processingFinished(self):
        thread = self.sender()
        self._output_variables = thread.output_variables
        self.trigger_downstream()

    def _setProgressValue(self, value):
        self._orangeProgress.widget.progressBarSet(value)

    def changeStaticInput(self):
        self.handleNewSignals()

    def handleNewSignals(self):
        self.run()
