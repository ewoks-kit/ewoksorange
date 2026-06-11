from time import sleep

import pytest
from ewokscore import Task

from ..gui.owwidgets.meta import ow_build_opts
from ..gui.owwidgets.threaded import (
    OWEwoksWidgetOneThreadPerRun as _OWEwoksWidgetOneThreadPerRun,
)
from ..gui.qt_utils.app import QtEvent
from .utils import DummyTask


class MyObject:
    def __init__(self):
        self.value = None
        self.finished = QtEvent()

    def finished_callback(self):
        self.finished.set()


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
        ("cancellation_task_by_task", ["cancelled", "cancelled", "cancelled"]),
        ("cancellation_all_tasks", ["cancelled", "cancelled", "cancelled"]),
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

    futures = []
    for value, obj in enumerate(objects):
        widget.set_dynamic_input("value", value)
        widget.set_dynamic_input("my_object", obj)
        if test_case in ("cancellation_task_by_task", "cancellation_all_tasks"):
            widget.set_dynamic_input("sleep_duration", 0.5)

        # Start calculation
        futures.append(widget.execute_ewoks_task())

    if test_case == "cancellation_task_by_task":
        for exec_id in futures:
            widget.cancel_task(exec_id)
    elif test_case == "cancellation_all_tasks":
        widget.cancel_all_tasks()

    for obj in objects:
        obj.finished.wait(timeout=3)

    values = [obj.value for obj in objects]
    assert values == expected_values
