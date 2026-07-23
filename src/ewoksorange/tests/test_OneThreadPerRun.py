from time import sleep

import pytest

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
    "test_case, expected_obj_values",
    [
        (
            "standard_execution",
            [0, 1, 2],
        ),
        (
            "cancel_futures",
            ["cancelled", "cancelled", "cancelled"],
        ),
    ],
)
def test_OWEwoksWidgetOneThreadPerRun(qtapp, test_case, expected_obj_values):
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
        if test_case == "cancel_futures":
            widget.set_dynamic_input("sleep_duration", 0.5)

        # Start calculation
        futures.append(widget.execute_ewoks_task())

    if test_case == "cancel_futures":
        # Wait for the future to start.
        sleep(0.2)
        for future in futures:
            assert future.abort(), "Future cannot be aborted."
    for obj in objects:
        obj.finished.wait(timeout=3)

    values = [obj.value for obj in objects]
    assert values == expected_obj_values

    for future, expected_value in zip(futures, expected_obj_values):
        assert future.done(), "future is done"
        my_object_instance = future.result()["my_object"].value
        assert (
            my_object_instance.value == expected_value
        ), f"future result is {future.result()!r} when {expected_value!r} expected."
