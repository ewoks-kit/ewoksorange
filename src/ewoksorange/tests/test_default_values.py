import gc
import weakref
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


class MutableInputModel(BaseInputModel):
    roi: List[int] = Field(default=[0, 10])
    tags: List[str] = Field(default_factory=lambda: ["tag"])


class TaskWithMutableDefaults(
    Task, input_model=MutableInputModel, output_names=["tags"]
):
    def run(self):
        self.outputs.tags = self.inputs.tags


class EwoksOrangeMutableDefaults(
    OWEwoksWidgetNoThread, ewokstaskclass=TaskWithMutableDefaults
):
    name = "ewoks widget with mutable defaults"


def test_default_values(qtbot):
    """
    Test that task with an ewoks InputModel are taking into account field default values.

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

    assert widget_a.get_default_input_value("a") == 12
    assert widget_a.get_default_input_value("b") == ("b",)
    assert widget_a.get_default_input_values() == {
        "a": 12,
        "b": ("b",),
    }
    assert widget_a.get_default_input_value("c", "unset") == "unset"


def test_removed_default_value(qtbot):
    """A default input removed from the widget falls back to the model default."""
    widget = EwoksOrangeTaskA()
    qtbot.addWidget(widget)

    widget.set_default_input("a", 99)
    assert widget.get_default_input_value("a") == 99

    widget.set_default_input("a", None)
    assert widget.get_default_input_value("a") == 12
    assert widget.get_default_input_values() == {"a": 12, "b": ("b",)}


def test_default_values_do_not_keep_widget_alive(qtbot):
    """Getting the model default values does not keep a reference to the widget."""
    widget = EwoksOrangeTaskA()
    qtbot.addWidget(widget)
    assert widget.get_default_input_value("a") == 12

    widget_ref = weakref.ref(widget)
    del widget
    gc.collect()
    assert widget_ref() is None


def test_mutable_default_values(qtbot):
    """Modifying a default value of a widget does not modify the model default.

    Fields with a default factory have no widget default..
    """
    widget = EwoksOrangeMutableDefaults()
    qtbot.addWidget(widget)
    assert widget.get_default_input_values() == {"roi": [0, 10]}

    widget.get_default_input_value("roi").append(99)
    widget.get_default_input_values()["roi"].append(99)

    assert widget.get_default_input_value("roi") == [0, 10]
    assert EwoksOrangeMutableDefaults().get_default_input_value("roi") == [0, 10]
    assert MutableInputModel().roi == [0, 10]


def test_default_factory_values(qtbot):
    """Fields with a default factory have no widget default but the task gets the factory value."""
    widget = EwoksOrangeMutableDefaults()
    qtbot.addWidget(widget)
    assert widget.get_default_input_value("tags", "unset") == "unset"
    assert "tags" not in widget.get_default_input_values()
    assert "tags" not in widget.get_task_input_values()

    task_future = widget.execute_ewoks_task()
    assert task_future.output_values() == {"tags": ["tag"]}
