from ewokscore import Task

from time import sleep
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


def test_OWEwoksWidgetOneThreadPerRun_cancellation(qtapp):
    # test task cancellation
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
        widget.set_dynamic_input("sleep_duration", 0.5)

        # Start calculation
        task_exec_id = widget.execute_ewoks_task()
        execution_ids.append(task_exec_id)
        assert task_exec_id not in ("", None)

    for exec_id in execution_ids:
        widget.cancel_task(exec_id)

    for obj in objects:
        obj.finished.wait(timeout=3)

    # The task is not implemented the `cancel` method,
    # so the first task will be executed and the others will be cancelled.
    values = [obj.value for obj in objects]
    expected = ["cancelled", "cancelled", "cancelled"]
    assert values == expected
