from time import sleep

import pytest
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
    optional_input_names=("sleep_duration",),
    output_names=("my_object",),
):
    """Task that set a value to MyObject and set a 'finished' Event"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__cancelled = False

    def run(self):
        sleep(self.input_values.get("sleep_duration", 0))
        my_object = self.inputs.my_object

        if self.__cancelled:
            my_object.value = "cancelled"
        else:
            my_object.value = self.inputs.value
        self.outputs.my_object = my_object
        my_object.finished_callback()

    def cancel(self):
        self.__cancelled = True


class OWEwoksWidgetOneThreadPerRun(
    _OWEwoksWidgetOneThreadPerRun,
    **ow_build_opts,
    ewokstaskclass=DummyTask,
):
    name = "test_OW"


@pytest.mark.parametrize(
    "test_case, expected_values",
    [
        ("standard_execution", [0, 1, 2]),
        ("cancellation", ["cancelled", "cancelled", "cancelled"]),
    ],
)
def test_OWEwoksWidgetOneThreadPerRun(qtapp, test_case, expected_values):
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

    execution_ids = []
    for value, obj in enumerate(objects):
        widget.set_dynamic_input("value", value)
        widget.set_dynamic_input("my_object", obj)
        if test_case == "cancellation":
            widget.set_dynamic_input("sleep_duration", 0.5)

        # Start calculation
        execution_ids.append(widget.execute_ewoks_task())

    if test_case == "cancellation":
        for exec_id in execution_ids:
            widget.cancel_task(exec_id)

    for obj in objects:
        obj.finished.wait(timeout=3)

    values = [obj.value for obj in objects]
    assert values == expected_values
