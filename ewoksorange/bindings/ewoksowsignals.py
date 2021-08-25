import inspect
from Orange.widgets.widget import Input, Output


SIGNAL_TYPES = (Input, Output)


def is_signal(obj):
    return isinstance(obj, SIGNAL_TYPES)


def get_signals(signals_class) -> dict:
    # TODO: getsignals doesn't work in the Orange3 hard-fork
    # from orangewidget.utils.signals import getsignals
    # return dict(getsignals(signals_class))
    return dict(inspect.getmembers(signals_class, is_signal))


def signal_ewoks_to_orange_name(signals_class, ewoskname: str) -> str:
    try:
        return getattr(signals_class, ewoskname).name
    except AttributeError:
        raise RuntimeError(f"{ewoskname} is not a signal of {signals_class}")


def signal_orange_to_ewoks_name(signals_class, orangename: str) -> str:
    for ewoskname, signal in get_signals(signals_class).items():
        if signal.name == orangename:
            return ewoskname
    raise RuntimeError(f"{orangename} is not a signal of {signals_class}")


def receiveDynamicInputs(name):
    setter_name = f"{name}_ewoks_setter"

    def setter(self, value):
        # Called by the SignalManager as a result of calling
        # `send` on an upstream output.
        self.receiveDynamicInputs(name, value)

    setter.__name__ = setter_name
    return setter


def _validate_signals(namespace, direction, names):
    signals_class_name = direction.title()
    is_inputs = direction == "inputs"
    signals_class = namespace[signals_class_name]
    signals = get_signals(signals_class)
    for ewoksname in names:
        signal = signals.pop(ewoksname, None)
        if signal is None:
            if is_inputs:
                signal = Input(name=ewoksname, type=object)
            else:
                signal = Output(name=ewoksname, type=object)
            setattr(signals_class, ewoksname, signal)
        signal.ewoksname = ewoksname
        if is_inputs and not signal.handler:  # str
            setter = receiveDynamicInputs(ewoksname)
            namespace[setter.__name__] = signal(setter)


def validate_inputs(namespace):
    if "Inputs" not in namespace:

        class Inputs:
            pass

        namespace["Inputs"] = Inputs

    _validate_signals(namespace, "inputs", namespace["ewokstaskclass"].input_names())


def validate_outputs(namespace):
    if "Outputs" not in namespace:

        class Outputs:
            pass

        namespace["Outputs"] = Outputs

    _validate_signals(namespace, "outputs", namespace["ewokstaskclass"].output_names())
