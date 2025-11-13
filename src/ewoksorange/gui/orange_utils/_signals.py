"""
Orange behavior:

- The widget instance attributes `Inputs` and `Outputs` are instances of the widget class attributes `Inputs` and `Outputs`.
- The `Input` and `Output` attributes of the `Inputs` and `Outputs` instances hold a reference to the widget.
- `Input` and `Output` attributes have two names: orange name and Inputs/Outputs container attribute name.
- Old-style `inputs` and `outputs` are deprecated but can still exist.

Ewoks-Orange behavior:

- `Input` and `Output` attributes have three names: orange name, ewoks name and Inputs/Outputs container attribute name.

Oasys behavior:

- Does not use `Inputs` or `Outputs` class, it uses lists for tuples or dicts. We create the
  `Inputs` and `Outputs` classes for ewoksorange but Oasys does not use them.

Nomenclature:

- Instances of `Input` and `Output` are referred to as "signals".

Implementation:

- When Orange instantiates a widget, it calls `OWBaseWidget._bind_signals` to sets the `Inputs` and `Outputs` attributes
  of the widget instance to be `Inputs` and `Outputs` instances. Thats why in this module we have methods that accept
  widget or signal container classes and instances:

  .. code--block:: python

    signal_container: Union[str, object]
    orange_widget: Union[OWBaseWidget, Type[OWBaseWidget]]
"""

import inspect
from typing import Callable
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional
from typing import Tuple
from typing import Type
from typing import Union
from typing import get_origin

from pydantic import BaseModel

from ...orange_version import ORANGE_VERSION
from .orange_imports import OWBaseWidget
from .signals import Input
from .signals import Output
from .signals import _InputSignal
from .signals import _OutputSignal

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:

    def _native_getsignals(
        signal_container_class: type,
    ) -> Union[List[Tuple[str, Input]], List[Tuple[str, Output]]]:
        # Copied from the latest orange-widget-base
        return [
            (k, v)
            for cls in reversed(inspect.getmro(signal_container_class))
            for k, v in cls.__dict__.items()
            if isinstance(v, (Input, Output))
        ]

else:
    from orangewidget.utils.signals import getsignals as _native_getsignals


def _get_signals(
    signal_container: Union[type, object],
) -> Union[List[Tuple[str, Input]], List[Tuple[str, Output]]]:
    if isinstance(signal_container, type):
        lst = _native_getsignals(signal_container)
    else:
        lst = _native_getsignals(type(signal_container))
        lst = [(name, getattr(signal_container, name)) for name, _ in lst]
    return lst


def get_signal_list(
    orange_widget: Union[OWBaseWidget, Type[OWBaseWidget]],
    direction: Literal["inputs", "outputs"],
) -> Union[List[Input], List[Output]]:
    """Returns list of Input or Output signal instances."""
    signal_container = _get_signal_container(orange_widget, direction)
    return _get_signal_list_from_container(signal_container)


def _get_signal_list_from_container(
    signal_container: Union[type, object],
) -> Union[List[Input], List[Output]]:
    """Returns list of Input or Output signal instances."""
    signal_list = []
    counter = 0
    for attrname, signal in _get_signals(signal_container):
        if not getattr(signal, "ewoksname", ""):
            # Most likely a native Orange/Oasys widget
            signal.ewoksname = attrname

        if getattr(signal, "_seq_id"):
            signal_list.append((signal._seq_id, signal))
        else:
            # Most likely a native Oasys widget
            counter += 1
            signal_list.append((counter, signal))

    return [signal for _, signal in sorted(signal_list, key=lambda tpl: tpl[0])]


def _get_signal_ewoks_dict(
    signal_container: Union[str, object],
) -> Dict[str, Union[List[Input], List[Output]]]:
    """Returns dict of Input or Output signal instances.
    The keys are the ewoks names or attribute names when missing.
    """
    signal_dict = {}
    for attrname, signal in _get_signals(signal_container):
        if not getattr(signal, "ewoksname", ""):
            # Most likely a native Orange widget
            signal.ewoksname = attrname
        signal_dict[signal.ewoksname] = signal
    return signal_dict


def _get_signal_container(
    orange_widget: Union[OWBaseWidget, Type[OWBaseWidget]],
    direction: Literal["inputs", "outputs"],
) -> Union[type, object]:
    """Returns attribute which is a class with Input or Output signal instances as attributes."""
    attr_name = direction.title()

    signal_container_class = None

    if hasattr(orange_widget, direction):
        if not hasattr(orange_widget, attr_name) or not _get_signals(
            getattr(orange_widget, attr_name)
        ):
            # Most likely a native Orange/Oasys widget.
            # Old-style inputs/outputs as a list of tuples or dicts
            # instead of the new-style Inputs/Outputs classes.
            # Old-style is deprecated in Orange.
            signals = getattr(orange_widget, direction)
            signal_container_class = _oldstyle_signal_container(signals, direction)
    else:
        if not hasattr(orange_widget, attr_name):
            signal_container_class = type(attr_name, (), {})

    if signal_container_class is not None:
        if isinstance(orange_widget, type):
            setattr(orange_widget, attr_name, signal_container_class)
        else:
            setattr(orange_widget, attr_name, signal_container_class())

    return getattr(orange_widget, attr_name)


def get_signal_orange_names(
    orange_widget: Union[OWBaseWidget, Type[OWBaseWidget]],
    direction: Literal["inputs", "outputs"],
) -> List[str]:
    """Returns the Orange input or output names, not the Ewoks names."""
    signals = get_signal_list(orange_widget, direction)
    return [signal.name for signal in signals]


def signal_ewoks_to_orange_name(
    orange_widget: Union[OWBaseWidget, Type[OWBaseWidget]],
    direction: Literal["inputs", "outputs"],
    ewoksname: str,
) -> str:
    """Returns the Orange input or output name."""
    signal_container = _get_signal_container(orange_widget, direction)
    signal_dict = _get_signal_ewoks_dict(signal_container)
    if ewoksname not in signal_dict:
        raise RuntimeError(
            f"{ewoksname} is not a signal of {signal_container} of {orange_widget}"
        )
    return signal_dict[ewoksname].name


def signal_orange_to_ewoks_name(
    orange_widget: Union[OWBaseWidget, Type[OWBaseWidget]],
    direction: Literal["inputs", "outputs"],
    orangename: str,
) -> str:
    """Returns the Ewoks name or the `Inputs` or `Outputs` attribute name."""
    signal_container = _get_signal_container(orange_widget, direction)
    signal_dict = _get_signal_ewoks_dict(signal_container)
    for ewoks_or_attr_name, signal in signal_dict.items():
        if signal.name == orangename:
            return ewoks_or_attr_name
    raise RuntimeError(f"{orangename} is not a signal of {signal_container}")


def get_signal(
    orange_widget: Union[OWBaseWidget, Type[OWBaseWidget]],
    direction: Literal["inputs", "outputs"],
    ewoksname: str,
) -> Union[Input, Output]:
    signal_container = _get_signal_container(orange_widget, direction)
    signal_dict = _get_signal_ewoks_dict(signal_container)
    if ewoksname not in signal_dict:
        raise ValueError(
            f"{orange_widget.__name__} does not have {ewoksname!r} in the {direction.title()!r}"
        )
    return signal_dict[ewoksname]


def _receive_dynamic_input(name: str) -> Callable:
    setter_name = f"{name}_ewoks_input_setter"

    def setter(self, value):
        # Called by the SignalManager as a result of calling
        # `send` on an upstream output.
        self.set_dynamic_input(name, value)

    setter.__name__ = setter_name
    return setter


def validate_signals(
    namespace: dict, direction: Literal["inputs", "outputs"], name_to_ignore=tuple()
) -> None:
    """Namespace of an Ewoks-Orange widget class (i.e. not a native Orange widget):

    - Ensure that for each Ewoks Task input and output there is an Orange widget signal.
    - Ensure that the `Inputs`/`Outputs` namespace key exist.
    - Oasys: ensure that the `inputs`/`outputs` namespace key exist.
    """
    ewoks_task = namespace["ewokstaskclass"]
    if direction == "inputs":
        signal_class = Input
        ewoks_names = ewoks_task.input_names()
        ewoks_model = ewoks_task.input_model()
        is_input = True
    elif direction == "outputs":
        signal_class = Output
        ewoks_names = ewoks_task.output_names()
        ewoks_model = ewoks_task.output_model()
        is_input = False
    else:
        raise ValueError(f"{direction=}")
    ewoks_names = tuple(name for name in ewoks_names if name not in name_to_ignore)

    # Do not allow old-style (list instead of signal class) signal definition in Ewoks-Orange widgets.
    signal_container_name = direction.title()
    if direction in namespace:
        raise ValueError(
            f"Use an {signal_container_name!r} class instead of an {direction!r} list"
        )

    # Ensure signal container attribute exists
    if signal_container_name not in namespace:
        namespace[signal_container_name] = type(signal_container_name, (), {})

    # Orange signals
    signal_container_class = namespace[signal_container_name]
    signals_dict = _get_signal_ewoks_dict(signal_container_class)

    # Validate signal container
    signals_attrs = list()
    new_signals_class = False
    for ewoksname in ewoks_names:
        # Orange signal for the Ewoks variable.
        signal = signals_dict.get(ewoksname, None)
        if signal is None:
            data_type = _pydantic_model_field_type(ewoks_model, ewoksname)
            doc = _pydantic_model_field_doc(
                ewoks_model,
                ewoksname,
            )
            orangename = ewoksname
            signal = signal_class(name=orangename, type=data_type, doc=doc)
            new_signals_class = True

        if is_input:
            # Create a handler for the input value provided
            # by upstream nodes at runtime, unless already provided.
            handler: str = signal.handler
            if not handler or handler not in namespace:
                setter = _receive_dynamic_input(ewoksname)
                handler = setter.__name__
                namespace[handler] = signal(setter)  # does input.handler = handler

        # Ensure the signal knows about the Ewoks parameter name as well
        signal.ewoksname = ewoksname

        signals_attrs.append((ewoksname, signal))

    # Ensure Ewoks order
    for i, (_, signal) in enumerate(signals_attrs, 1):
        signal._seq_id = i

    # Replace signal class when needed
    if new_signals_class:
        signal_container_class = type(signal_container_name, (), dict(signals_attrs))
        namespace[signal_container_name] = signal_container_class

    # Oasys needs old-style signal definitions
    if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
        if len(namespace.get(direction, [])) != len(ewoks_names):
            namespace[direction] = _oldstyle_signal_list(signal_container_class)


def _pydantic_model_field_type(
    model: Optional[Type[BaseModel]], field_name: str, default_data_type=object
) -> type:
    if model is None:
        return default_data_type
    field_info = model.model_fields.get(field_name, None)
    if field_info is None:
        return default_data_type
    origin = get_origin(field_info.annotation)
    if origin is None:
        # if unsupported ()
        return field_info.annotation
    elif origin in (list, tuple):
        return origin
    else:
        # Union, Optional, Literal use cases
        return object


def _pydantic_model_field_doc(
    model: Optional[Type[BaseModel]], field_name: str, default_doc=None
) -> Optional[str]:
    if model is None:
        return default_doc
    field_info = model.model_fields.get(field_name, None)
    if field_info is None:
        return default_doc
    try:
        return field_info.description
    except AttributeError:
        return default_doc


def _oldstyle_signal_container(
    signals: List[Tuple[str]], direction: Literal["inputs", "outputs"]
) -> type:
    """Convert

    .. code-block:: python

        inputs = [("A", object, ""), ("B", object, "")]  # list of tuples or dicts

    to

    .. code-block:: python

        class Inputs:
            a = Input("A", object)
            b = Input("B", object)
    """
    if direction == "inputs":
        prefix = "input"
        signal_class = Input
    elif direction == "outputs":
        prefix = "output"
        signal_class = Output
    else:
        raise ValueError(f"{direction=}")
    names = [f"{prefix}{i}" for i in range(len(signals))]
    values = [_oldstyle_instantiate_signal(signal_class, signal) for signal in signals]
    attrs = dict(zip(names, values))
    return type(direction.title(), (), attrs)


def _oldstyle_signal_list(input_container_class) -> List[str]:
    """Convert

    .. code-block:: python

        class Inputs:
            a = Input("A", object)
            b = Input("B", object)

    to

    .. code-block:: python

        inputs = [("A", object, "")]
    """
    signals = _get_signal_list_from_container(input_container_class)
    return [signal.as_tuple() for signal in signals]


def _oldstyle_instantiate_signal(
    signal_class: Union[Type[Input], Type[Output]], data: Union[tuple, dict]
) -> Union[Input, Output]:
    if isinstance(data, tuple):
        signal = signal_class(*data, ewoksname=data[0])
    elif isinstance(data, dict):
        signal = signal_class(**data, ewoksname=data["name"])
    elif isinstance(data, _InputSignal):
        names = "name", "type", "id", "doc", "replaces"
        data_dict = {name: getattr(data, name) for name in names if hasattr(data, name)}
        signal = signal_class(**data_dict)
        if hasattr(data, "handler"):
            signal.handler = getattr(data, "handler")
        signal.ewoksname = signal.name
    elif isinstance(data, _OutputSignal):
        names = "name", "type", "id", "doc", "replaces"
        data_dict = {name: getattr(data, name) for name in names if hasattr(data, name)}
        signal = signal_class(**data_dict)
        signal.ewoksname = signal.name
    else:
        raise TypeError(type(data))
    return signal
