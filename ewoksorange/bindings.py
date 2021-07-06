import os
import sys
import tempfile

from Orange.canvas.__main__ import main as launchcanvas

from Orange.widgets.widget import OWWidget, WidgetMetaClass
from Orange.widgets.widget import Input, Output
from Orange.widgets.settings import Setting

from ewokscore import load_graph
from ewokscore.variable import Variable
from ewokscore.task import TaskInputError
from . import owsconvert


__all__ = ["execute_graph", "OWEwoksWidget"]


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
    attr["varinfo"] = Setting({"root_uri": "/tmp"})
    attr["static_input"].schema_only = True
    attr["varinfo"].schema_only = True

    if inputnamemap is None:
        inputnamemap = inputnamemap
    if outputnamemap is None:
        outputnamemap = outputnamemap

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


class OWEwoksWidgetMetaClass(WidgetMetaClass):
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


class OWEwoksWidget(OWWidget, metaclass=OWEwoksWidgetMetaClass, openclass=True):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.dynamic_input_variables = dict()
        self.output_variables = dict()

    @classmethod
    def input_names(cls):
        return cls.ewokstaskclass.input_names()

    @classmethod
    def output_names(cls):
        return cls.ewokstaskclass.output_names()

    @property
    def input_variables(self):
        variables = dict()
        for name in self.input_names():
            var = self.dynamic_input_variables.get(name)
            if var is None or var.value is None:
                value = self.static_input.get(name)
                var = Variable(value=value)
            variables[name] = var
        return variables

    @property
    def input_values(self):
        return {k: v.value for k, v in self.input_variables.items()}

    @property
    def dynamic_input_values(self):
        return {k: v.value for k, v in self.dynamic_input_variables.items()}

    @property
    def output_values(self):
        return {k: v.value for k, v in self.output_variables.items()}

    def set_input(self, name, var):
        if var is None:
            self.dynamic_input_variables.pop(name, None)
        else:
            if not isinstance(var, Variable):
                raise TypeError(var, Variable)
            self.dynamic_input_variables[name] = var

    def trigger_downstream(self):
        for name, var in self.output_variables.items():
            channel = getattr(self.Outputs, name)
            if var.value is None:
                channel.send(None)  # or invalidate?
            else:
                channel.send(var)

    def clear_downstream(self):
        for name in self.output_variables:
            channel = getattr(self.Outputs, name)
            channel.send(None)  # or invalidate?

    def run(self):
        task = self.ewokstaskclass(inputs=self.input_variables, varinfo=self.varinfo)
        try:
            task.execute()
        except TaskInputError:
            self.clear_downstream()
            return
        except Exception:
            self.clear_downstream()
            raise
        self.output_variables = task.output_variables
        self.trigger_downstream()

    def changeStaticInput(self):
        self.handleNewSignals()

    def handleNewSignals(self):
        self.run()


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
