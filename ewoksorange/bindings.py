import os
import sys
import tempfile

from Orange.canvas.__main__ import main as launchcanvas
from Orange.widgets.widget import OWWidget, WidgetMetaClass
from Orange.widgets.widget import Input, Output
from Orange.widgets.settings import Setting
from Orange.widgets import gui
from AnyQt.QtCore import QThread
from ewokscore import load_graph
from ewokscore.variable import Variable
from ewokscore.task import TaskInputError
from ewokscore.hashing import UniversalHashable
from ewokscore.hashing import MissingData
from AnyQt.QtCore import pyqtSignal as Signal
import inspect
from . import owsconvert
import logging

_logger = logging.getLogger(__name__)


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
        {name: MISSING_DATA for name in ewokstaskclass.input_names()}
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
if "openclass" in inspect.getargspec(WidgetMetaClass)[0]:
    ow_build_opts["openclass"] = True


class _OWEwoksBaseWidget(OWWidget, metaclass=_OWEwoksWidgetMetaClass, **ow_build_opts):
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
    def input_values(self):
        return {k: self._get_value(v) for k, v in self._all_inputs.items()}

    @property
    def static_input_values(self):
        # Warning: do not use static_input directly because it
        #          messes up MISSING_DATA
        return {k: self._get_value(v) for k, v in self.static_input.items()}

    @property
    def dynamic_input_values(self):
        return {k: self._get_value(v) for k, v in self._dynamic_inputs.items()}

    @property
    def output_values(self):
        return {k: v.value for k, v in self._output_variables.items()}

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


class OWEwoksWidgetNoThread(_OWEwoksBaseWidget):
    """Widget which will run the ewokscore.Task directly"""

    def changeStaticInput(self):
        self.handleNewSignals()

    def handleNewSignals(self):
        self.run()

    def run(self):
        try:
            task = self.ewokstaskclass(inputs=self._all_inputs, varinfo=self.varinfo)
        except TaskInputError:
            self.clear_downstream()
            return
        if not task.is_ready_to_execute:
            self.clear_downstream()
            return
        try:
            task.execute()
        except TaskInputError:
            self.clear_downstream()
            return
        except Exception:
            self.clear_downstream()
            raise
        self._output_variables = task.output_variables
        self.trigger_downstream()


class OWEwoksWidgetOneThread(_OWEwoksBaseWidget):
    """
    All the processing is done on one thread.
    If a processing is requested when the thread is already running then
    it is refused.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self._progress = gui.ProgressBar(self, 100)
        self._processingThread = _ProcessingThread(ewokstaskclass=self.ewokstaskclass)
        self._processingThread.sigProgress.connect(self._setProgressValue)
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
        self._progress.widget.progressBarSet(value)

    def _processingFinished(self):
        self._output_variables = self._processingThread.output_variables
        self.trigger_downstream()

    def changeStaticInput(self):
        self.handleNewSignals()

    def handleNewSignals(self):
        self.run()


class OWEwoksWidgetOneThreadPerRun(_OWEwoksBaseWidget):
    pass


class OWEwoksWidgetWithTaskStack(_OWEwoksBaseWidget):
    pass


class _ProcessingThread(QThread):
    sigProgress = Signal(int)
    """processing advancement. Expected value should be in [0, 100]"""

    def __init__(self, ewokstaskclass, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lastProgress = None
        self._ewokstaskclass = ewokstaskclass
        self._varinfo = None
        self._inputs = None
        self._output_variables = None
        self._task = None

    @property
    def ewokstaskclass(self):
        return self._ewokstaskclass

    @property
    def varinfo(self):
        return self._varinfo

    @property
    def inputs(self):
        return self._inputs

    @property
    def output_values(self):
        return {k: v.value for k, v in self._output_variables.items()}

    @property
    def task(self):
        return self._task

    @property
    def output_variables(self):
        return self._output_variables

    def init(self, varinfo=None, inputs=None):
        self._varinfo = varinfo
        self._inputs = inputs
        self._output_variables = dict()

    def update_progress(self, progress: float):
        if self._lastProgress != int(progress):
            self._lastProgress = int(progress)
            self.sigProgress.emit(progress)

    def run(self):
        self._task = self.ewokstaskclass(inputs=self.inputs, varinfo=self.varinfo)
        try:
            self._task = self.ewokstaskclass(inputs=self.inputs, varinfo=self.varinfo)
        except TaskInputError as e:
            _logger.warning(e)
            return
        if not self.task.is_ready_to_execute:
            return
        try:
            self.task.execute()
        except TaskInputError as e:
            _logger.warning(e)
            return
        except Exception:
            raise
        self._output_variables = self.task.output_variables


def execute_graph(graph, representation=None, varinfo=None):
    ewoksgraph = load_graph(source=graph, representation=representation)
    if ewoksgraph.is_cyclic:
        raise RuntimeError("Orange can only execute DAGs")
    if ewoksgraph.has_conditional_links:
        raise RuntimeError("Orange cannot handle conditional links")

    # We do not have a mapping between OWS and the runtime representation.
    # So map to a (temporary) persistent representation first.
    with tempfile.TemporaryDirectory() as tmpdirname:
        filename = os.path.join(tmpdirname, "ewokstaskgraph.ows")
        owsconvert.ewoks_to_ows(ewoksgraph, filename, varinfo=varinfo)
        argv = [sys.argv[0], filename]
        launchcanvas(argv=argv)
