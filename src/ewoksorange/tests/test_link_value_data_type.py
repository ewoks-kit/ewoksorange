from enum import Enum
from typing import List
from typing import Literal
from typing import Optional
from typing import Tuple
from typing import Union

import numpy
from ewokscore.model import BaseInputModel
from ewokscore.model import BaseOutputModel
from ewokscore.task import Task
from ewoksutils.import_utils import qualname
from orangecanvas.utils import qualified_name

from ewoksorange.gui.owwidgets.nothread import OWEwoksWidgetNoThread
from ewoksorange.gui.owwidgets.registration import _temporary_widget_discovery_object
from ewoksorange.gui.owwidgets.registration import register_owwidget

from ..orange_version import ORANGE_VERSION


class Data:
    pass


class MyEnum(Enum):
    VALUE = "value"


class InputModelA(BaseInputModel):
    a: int
    b: Tuple[int]
    c: List[float]
    d: Literal[42, "any"]


class OutputModelA(BaseOutputModel):
    a: float
    b: Data


class InputModelB(BaseInputModel):
    a: Union[float, int]
    b: Optional[numpy.float32]
    c: numpy.int32
    d: str
    e: MyEnum


class TaskA(
    Task,
    input_model=InputModelA,
    output_model=OutputModelA,
):
    def run(self):
        self.outputs.b = float(self.inputs.a)


class TaskB(
    Task,
    input_model=InputModelB,
):
    pass


class EwoksOrangeTaskA(OWEwoksWidgetNoThread, ewokstaskclass=TaskA):
    name = "ewoks widget A"


class EwoksOrangeTaskB(OWEwoksWidgetNoThread, ewokstaskclass=TaskB):
    name = "ewoks widget B"


def test_link_value_data_type(tmpdir, ewoks_orange_canvas):
    """Test that Orange link are correctly taking into account the ewoks input / output models."""
    widget_registry = _temporary_widget_discovery_object()

    for widget in (EwoksOrangeTaskA, EwoksOrangeTaskB):
        register_owwidget(
            widget_class=widget,
            package_name="ewoksorange",
            category_name="test",
            project_name="ewoksorange",
            discovery_object=widget_registry,
        )

    def get_input_data_type(widget_description, name):
        inputs = tuple(filter(lambda var: var.name == name, widget_description.inputs))
        assert len(inputs) == 1
        return inputs[0].type

    def get_output_data_type(widget_description, name):
        outputs = tuple(
            filter(lambda var: var.name == name, widget_description.outputs)
        )
        assert len(outputs) == 1
        return outputs[0].type

    def expected_output_type(dtype):
        if ORANGE_VERSION != ORANGE_VERSION.oasys_fork:
            return (dtype,)
        else:
            return dtype

    assert len(widget_registry.registry.widgets()) == 2

    # check that orange links are correctly typed.
    descWidgetA = widget_registry.registry.widget(qualname(EwoksOrangeTaskA))

    assert len(descWidgetA.inputs) == 4

    assert get_input_data_type(descWidgetA, "a") == expected_output_type(
        qualified_name(int)
    )
    assert get_input_data_type(descWidgetA, "b") == expected_output_type(
        qualified_name(tuple)
    )
    assert get_input_data_type(descWidgetA, "c") == expected_output_type(
        qualified_name(list)
    )
    assert get_input_data_type(descWidgetA, "d") == expected_output_type(
        qualified_name(object)
    )

    assert len(descWidgetA.outputs) == 2
    assert get_output_data_type(descWidgetA, "a") == expected_output_type(
        qualified_name(float)
    )
    assert get_output_data_type(descWidgetA, "b") == expected_output_type(
        qualified_name(Data)
    )

    descWidgetB = widget_registry.registry.widget(qualname(EwoksOrangeTaskB))
    assert len(descWidgetB.inputs) == 5
    assert get_input_data_type(descWidgetB, "a") == expected_output_type(
        qualified_name(object)
    )
    assert get_input_data_type(descWidgetB, "b") == expected_output_type(
        qualified_name(object)
    )
    assert get_input_data_type(descWidgetB, "c") == expected_output_type(
        qualified_name(numpy.int32)
    )
    assert get_input_data_type(descWidgetB, "d") == expected_output_type(
        qualified_name(str)
    )
    assert get_input_data_type(descWidgetB, "e") == expected_output_type(
        qualified_name(MyEnum)
    )

    assert len(descWidgetB.outputs) == 0
