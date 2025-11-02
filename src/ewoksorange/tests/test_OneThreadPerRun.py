from ewokscore import Task

from ..gui.owwidgets.meta import ow_build_opts
from ..gui.owwidgets.threaded import (
    OWEwoksWidgetOneThreadPerRun as _OWEwoksWidgetOneThreadPerRun,
)
from ..gui.qt_utils.app import QtEvent


class MyObject:
    def __init__(self):
        self.value = None
        self.finished = QtEvent()

    def finished_callback(self):
        self.finished.set()


class DummyTask(
    Task,
    input_names=("my_object", "value"),
    output_names=("my_object",),
):
    """Task that set a value to MyObject and set a 'finished' Event"""

    def run(self):
        my_object = self.inputs.my_object
        my_object.value = self.inputs.value
        self.outputs.my_object = my_object
        my_object.finished_callback()


class OWEwoksWidgetOneThreadPerRun(
    _OWEwoksWidgetOneThreadPerRun,
    **ow_build_opts,
    ewokstaskclass=DummyTask,
):
    name = "test_OW"


def test_OWEwoksWidgetOneThreadPerRun(qtapp):
    """
    Test processing several tasks.
    The widget will create one thread per task and execution will be done in parallel.
    Make sure all tasks are completed with valid outputs.
    """
    widget = OWEwoksWidgetOneThreadPerRun()

    objects = (
        MyObject(),
        MyObject(),
        MyObject(),
    )

    for value, obj in enumerate(objects):
        widget.set_dynamic_input("value", value)
        widget.set_dynamic_input("my_object", obj)

        # Start calculation
        widget.handleNewSignals()

    for obj in objects:
        obj.finished.wait(timeout=3)

    values = [obj.value for obj in objects]
    expected = [0, 1, 2]
    assert values == expected
