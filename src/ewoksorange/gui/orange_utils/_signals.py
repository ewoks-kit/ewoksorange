"""
Orange behavior:

- The widget instance attributes `Inputs` and `Outputs` are instances of the widget class attributes `Inputs` and `Outputs`.
- The `Input` and `Output` attributes of the `Inputs` and `Outputs` instances hold a reference to the widget.
- `Input` and `Output` attributes have two names: orange name and Inputs/Outputs container attribute name.

Ewoks-Orange behavior:

- `Input` and `Output` attributes have three names: orange name, ewoks name and Inputs/Outputs container attribute name.

Oasys behavior:

- Does not use `Inputs` or `Outputs` class, it uses lists for tuples or dicts. We create the
  `Inputs` and `Outputs` classes for ewoksorange but Oasys does not use them.

Nomenclature:

- Instances of `Input` and `Output` are referred to as "signals".
"""

import inspect
from typing import Any
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

if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:

    def _oasys_inputs_container(inputs: List[Tuple[str]]) -> type:
        """Convert

        .. code-block:: python

            inputs = [("A", object, ""), ("B", object, "")]  # list of tuples or dicts

        to

        .. code-block:: python

            class Inputs:
                a = Input("A", object)
                b = Input("B", object)
        """
        names = [f"input{i}" for i in range(len(inputs))]
        values = [_oasys_instantiate_signal(Input, input) for input in inputs]
        attrs = dict(zip(names, values))
        return type("Inputs", (), attrs)

    def _oasys_outputs_container(outputs: List[Dict[str, Any]]) -> type:
        """Convert

        .. code-block:: python

            outputs = [{"name": "A + B", "id": "A + B", "type": object}]  # list of tuples or dicts

        to

        .. code-block:: python

            class Outputs:
                result = Output("A + B", object)
        """
        names = [f"output{i}" for i in range(len(outputs))]
        values = [_oasys_instantiate_signal(Output, output) for output in outputs]
        attrs = dict(zip(names, values))
        return type("Outputs", (), attrs)

    def _oasys_inputs_list(input_container_class) -> List[str]:
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
        return [input.as_tuple() for input in signals]

    def _oasys_outputs_list(
        output_container_class: type,
    ) -> List[Dict[str, Any]]:
        """Convert

        .. code-block:: python

            class Outputs:
                result = Output("A + B", object)

        to

        .. code-block:: python

            outputs = [("A + B", object)]
        """
        signals = _get_signal_list_from_container(output_container_class)
        return [output.as_tuple() for output in signals]

    def _oasys_instantiate_signal(
        signal_class: Union[Type[Input], Type[Output]], data: Union[tuple, dict]
    ) -> Union[Input, Output]:
        if isinstance(data, tuple):
            signal = signal_class(*data, ewoksname=data[0])
        elif isinstance(data, dict):
            signal = signal_class(**data, ewoksname=data["name"])
        else:
            raise TypeError(type(data))
        return signal

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
            # Native Orange/Oasys widget
            signal.ewoksname = attrname

        if getattr(signal, "_seq_id"):
            signal_list.append((signal._seq_id, signal))
        else:
            # Native Oasys widget
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
            # Native Orange widget
            signal.ewoksname = attrname
        signal_dict[signal.ewoksname] = signal
    return signal_dict


def _get_signal_container(
    orange_widget: Union[OWBaseWidget, Type[OWBaseWidget]],
    direction: Literal["inputs", "outputs"],
) -> Union[type, object]:
    """Returns attribute which is a class with Input or Output signal instances as attributes."""
    attr_name = direction.title()

    if not hasattr(orange_widget, attr_name):
        if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
            if hasattr(orange_widget, direction):
                # Native Oasys widget: old-style inputs/outputs as a list of tuples or dicts
                # instead of the new-style Inputs/Outputs classes.
                signals = getattr(orange_widget, direction)
                if direction == "inputs":
                    signal_container_class = _oasys_inputs_container(signals)
                elif direction == "outputs":
                    signal_container_class = _oasys_outputs_container(signals)
                else:
                    raise ValueError(f"{direction=}")
            else:
                signal_container_class = type(attr_name, (), {})
        else:
            signal_container_class = type(attr_name, (), {})

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
            f"{orange_widget.__name__} does not have {ewoksname!r} in the {direction.Title()!r}"
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


def validate_inputs(namespace: dict, name_to_ignore=tuple()) -> None:
    """Namespace of an Ewoks-Orange widget class (i.e. not a native Orange widget):

    - Ensure that for each Ewoks Task input there is an Orange widget `Input` instance.
    - Ensure that `Inputs` namespace key exist.
    - Oasys: ensure that `inputs` namespace key exist.
    """

    ewoks_input_names = tuple(
        name
        for name in namespace["ewokstaskclass"].input_names()
        if name not in name_to_ignore
    )

    # Oasys: convert list of tuples to `Inputs` attribute
    if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
        if namespace.get("inputs"):
            raise ValueError("Use an `Inputs` class instead of an `inputs` list")

    # Ensure `Inputs` attribute exists
    if "Inputs" not in namespace:
        namespace["Inputs"] = type("Inputs", (), {})

    # Orange inputs
    input_container_class = namespace["Inputs"]
    inputs_dict = _get_signal_ewoks_dict(input_container_class)

    # Ewoks inputs
    ewoks_task = namespace.get("ewokstaskclass", None)
    input_model = ewoks_task.input_model()

    # Validate `Inputs`
    inputs_attrs = list()
    new_inputs_class = False
    for ewoksname in ewoks_input_names:
        # `Input` for the ewoks input
        input = inputs_dict.get(ewoksname, None)
        if input is None:
            data_type = _pydantic_model_field_type(input_model, ewoksname)
            doc = _pydantic_model_field_doc(
                input_model,
                ewoksname,
            )
            orangename = ewoksname
            input = Input(name=orangename, type=data_type, doc=doc)
            new_inputs_class = True

        # Create a handler for the input value provided
        # by upstream nodes at runtime, unless already provided.
        handler: str = input.handler
        if not handler or handler not in namespace:
            setter = _receive_dynamic_input(ewoksname)
            handler = setter.__name__
            namespace[handler] = input(setter)  # does input.handler = handler

        # Ensure the `Input` knows about the Ewoks parameter name as well
        input.ewoksname = ewoksname

        inputs_attrs.append((ewoksname, input))

    # Ensure Ewoks order
    for i, (_, input) in enumerate(inputs_attrs, 1):
        input._seq_id = i

    # Replace `Inputs` when needed
    if new_inputs_class:
        input_container_class = type("Inputs", (), dict(inputs_attrs))
        namespace["Inputs"] = input_container_class

    # Oasys: ensure list of tuples
    if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
        if len(namespace.get("inputs", [])) != len(ewoks_input_names):
            namespace["inputs"] = _oasys_inputs_list(input_container_class)


def validate_outputs(namespace: dict, name_to_ignore=tuple()) -> None:
    """Namespace of an Ewoks-Orange widget class (i.e. not a native Orange widget):

    - Ensure that for each Ewoks Task output there is an Orange widget `Output` instance.
    - Ensure that `Outputs` namespace key exist.
    - Oasys: ensure that `outputs` namespace key exist.
    """
    ewoks_output_names = tuple(
        name
        for name in namespace["ewokstaskclass"].output_names()
        if name not in name_to_ignore
    )

    # Oasys: convert list of tuples to `Outputs` attribute
    if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
        if namespace.get("outputs"):
            raise ValueError("Use an `Outputs` class instead of an `outputs` list")

    # Ensure `Outputs` attribute exists
    if "Outputs" not in namespace:
        namespace["Outputs"] = type("Outputs", (), {})

    # Orange outputs
    output_container_class = namespace["Outputs"]
    output_dict = _get_signal_ewoks_dict(output_container_class)

    # Ewoks inputs
    ewoks_task = namespace.get("ewokstaskclass", None)
    output_model = ewoks_task.output_model()

    # Validate `Outputs`
    outputs_attrs = list()
    new_outputs_class = False
    for ewoksname in ewoks_output_names:
        # `Output` for the ewoks output
        output = output_dict.get(ewoksname, None)
        if output is None:
            data_type = _pydantic_model_field_type(output_model, ewoksname)
            doc = _pydantic_model_field_doc(output_model, ewoksname)
            orangename = ewoksname
            output = Output(name=orangename, type=data_type, doc=doc)
            new_outputs_class = True

        # Ensure the `Output` knows about the Ewoks parameter name as well
        output.ewoksname = ewoksname

        outputs_attrs.append((ewoksname, output))

    # Ensure Ewoks order
    for i, (_, output) in enumerate(outputs_attrs, 1):
        output._seq_id = i

    # Replace `Outputs` when needed
    if new_outputs_class:
        output_container_class = type("Outputs", (), dict(outputs_attrs))
        namespace["Outputs"] = output_container_class

    # Oasys: ensure list of dicts
    if ORANGE_VERSION == ORANGE_VERSION.oasys_fork:
        if len(namespace.get("outputs", [])) != len(ewoks_output_names):
            namespace["outputs"] = _oasys_outputs_list(output_container_class)


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
