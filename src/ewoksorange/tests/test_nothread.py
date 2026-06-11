from time import sleep

import pytest
from ewokscore import Task

from ..gui.owwidgets.meta import ow_build_opts
from ..gui.owwidgets.nothread import OWEwoksWidgetNoThread as _OWEwoksWidgetNoThread
from ..gui.qt_utils.app import QtEvent
from .utils import DummyTask


class MyObject:
    def __init__(self):
        self.value = None
        self.finished = QtEvent()

    def finished_callback(self):
        self.finished.set()


class OWEwoksWidgetNoThread(
    _OWEwoksWidgetNoThread,
    **ow_build_opts,
    ewokstaskclass=DummyTask,
):
    name = "test_OW"


def test_OWEwoksWidgetNoThread(qtapp):
    """
    Test processing of two tasks.
    The first task will be executed, prevent any other execution of code. Then the second will aldo be executed.
    """
    widget = OWEwoksWidgetNoThread()

    objects = (
        MyObject(),
        MyObject(),
    )

    futures = []
    for value, obj in enumerate(objects):
        widget.set_dynamic_input("value", value)
        widget.set_dynamic_input("my_object", obj)
        widget.set_dynamic_input("sleep_duration", 0.5)

        # Start calculation
        futures.append(widget.execute_ewoks_task())

    future_task, concurrent_future_task = futures

    assert "my_object" in future_task.result()
    assert future_task.task_exec_id != concurrent_future_task.task_exec_id
    assert "my_object" in concurrent_future_task.result()
