from typing import List
from typing import Optional
from typing import Tuple

from ewokscore.model import BaseInputModel
from ewokscore.task import Task
from pydantic import Field

from ewoksorange.gui.owwidgets.nothread import OWEwoksWidgetNoThread
from ewoksorange.gui.owwidgets.registration import _temporary_widget_discovery_object
from ewoksorange.gui.owwidgets.registration import register_owwidget


class InputModel(BaseInputModel):
    a: int = Field(default=12)
    b: Tuple[str] = Field(
        default=("b",),
    )
    c: List[float]
    d: Optional[float] = Field(default=None)


class TaskA(
    Task,
    input_model=InputModel,
):
    def run(self):
        pass


class EwoksOrangeTaskA(OWEwoksWidgetNoThread, ewokstaskclass=TaskA):
    name = "ewoks widget A"


def test_default_values(ewoks_orange_canvas):
    """
    Test that task with an ewoks InputModel are taking into account field default values and default factory.

    Warning: Orange consider "None" as the value to 'invalidate' link. As a consequence those are filtered if defined as a default value.
    """
    widget_registry = _temporary_widget_discovery_object()

    for widget in (EwoksOrangeTaskA,):
        register_owwidget(
            widget_class=widget,
            package_name="ewoksorange",
            category_name="test",
            project_name="ewoksorange",
            discovery_object=widget_registry,
        )

    widget_a = EwoksOrangeTaskA()
    assert widget_a.get_default_input_values() == {
        "a": 12,
        "b": ("b",),
    }
