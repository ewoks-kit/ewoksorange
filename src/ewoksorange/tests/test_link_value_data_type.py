import pytest
from ewokscore.model import BaseInputModel
from ewokscore.model import BaseOutputModel
from ewokscore.task import Task
from ewoksutils.import_utils import qualname
from orangecanvas.utils import qualified_name

from ewoksorange.gui.owwidgets.nothread import OWEwoksWidgetNoThread
from ewoksorange.gui.owwidgets.registration import _temporary_widget_discovery_object
from ewoksorange.gui.owwidgets.registration import register_owwidget
from ewoksorange.gui.workflows.owscheme import ewoks_to_ows

from ..orange_version import ORANGE_VERSION


class InputModelA(BaseInputModel):
    a: int


class OutputModelA(BaseOutputModel):
    b: float


class InputModelB(BaseInputModel):
    c: float


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


@pytest.mark.skipif(
    ORANGE_VERSION == ORANGE_VERSION.oasys_fork, reason="hanging with oasys binding."
)
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

    assert len(widget_registry.registry.widgets()) == 2

    # check that orange links are correctly typed.
    descWidgetA = widget_registry.registry.widget(qualname(EwoksOrangeTaskA))

    assert len(descWidgetA.inputs) == 1
    assert descWidgetA.inputs[0].type == (qualified_name(int),)
    assert len(descWidgetA.outputs) == 1
    assert descWidgetA.outputs[0].type == (qualified_name(float),)
    descWidgetB = widget_registry.registry.widget(qualname(EwoksOrangeTaskB))
    assert len(descWidgetB.inputs) == 1
    assert descWidgetB.inputs[0].type == (qualified_name(float),)
    assert len(descWidgetB.outputs) == 0
