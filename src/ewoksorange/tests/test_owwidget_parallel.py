import time
from threading import Barrier

import numpy
import pytest
from ewokscore.task import Task
from ewoksutils.exceptions import TaskExecutionError

from ..gui.owwidgets.meta import ow_build_opts
from ..gui.owwidgets.threaded import OWEwoksWidgetOneThreadPerRun


class Cancelled(Exception):
    def __init__(self, value, tm) -> None:
        self.value = value
        self.time = tm
        super().__init__()


class Parallel(
    Task,
    input_names=["value", "sleep", "synchronize_run"],
    output_names=["value", "time"],
):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__cancel_requested = False

    def run(self):
        # Wait for all parallel task to start
        self.inputs.synchronize_run.wait(timeout=10)

        # Provide enough time to cancel the task
        time.sleep(self.inputs.sleep)

        tm = time.perf_counter()

        # Return value as output or exception
        if self.__cancel_requested:
            try:
                raise Cancelled(self.inputs.value, tm)
            finally:
                self.cancelled = True

        self.outputs.time = tm
        self.outputs.value = self.inputs.value

    def cancel(self):
        # Interpretation #1: self.cancelled is the state not the request
        self.__cancel_requested = True


class OWParallel(
    OWEwoksWidgetOneThreadPerRun, **ow_build_opts, ewokstaskclass=Parallel
):
    name = "test_OW"


def test_owwidget_parallel(qtapp):
    """Test parallel task execution."""
    widget = OWParallel()

    sleep_seconds = 0.5
    values = [0, 1, 2, 3]
    cancels = [False, True, False, False]
    synchronize_run = Barrier(len(values))

    # all jobs start when the last run method is called
    futures = []
    for value, cancel in zip(values, cancels):
        widget.set_dynamic_input("value", value)
        widget.set_dynamic_input("sleep", sleep_seconds)
        widget.set_dynamic_input("synchronize_run", synchronize_run)
        futures.append(widget.execute_ewoks_task())

    # cancel some jobs
    for future, cancel in zip(futures, cancels):
        if cancel:
            _ = future.abort()

    # check results
    times = []
    for future, value, cancel in zip(futures, values, cancels):
        if cancel:
            with pytest.raises(TaskExecutionError) as exc_info:
                _ = future.result(timeout=10)

            assert future.aborted()

            assert isinstance(exc_info.value.__cause__, Cancelled)
            assert exc_info.value.__cause__.value == value

            times.append(exc_info.value.__cause__.time)
        else:
            outputs = future.result(timeout=10)

            assert not future.aborted()

            assert outputs["value"].value == value
            times.append(outputs["time"].value)

    assert (numpy.diff(times) < 1.5 * sleep_seconds).all(), "not executed in parallel"
