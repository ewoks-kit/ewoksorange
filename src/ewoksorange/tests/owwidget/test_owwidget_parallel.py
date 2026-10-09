import time
from threading import Barrier

import numpy
import pytest
from ewokscore.task import Task
from ewoksutils.exceptions import TaskExecutionError

from ...gui.owwidgets.meta import ow_build_opts
from ...gui.owwidgets.threaded import OWEwoksWidgetOneThreadPerRun


class Stopped(Exception):
    def __init__(self, value, tm) -> None:
        self.value = value
        self.time = tm
        super().__init__()


class Parallel(
    Task,
    input_names=["value", "sleep", "synchronize_run"],
    output_names=["value", "time"],
):
    def run(self):
        # Wait for all parallel task to start
        self.inputs.synchronize_run.wait(timeout=10)

        # Provide enough time to request the task to stop
        time.sleep(self.inputs.sleep)

        tm = time.perf_counter()

        # Return value as output or exception
        if self.stop_requested:
            raise Stopped(self.inputs.value, tm)

        self.outputs.time = tm
        self.outputs.value = self.inputs.value

    def _on_stop_requested(self):
        # Nothing to do: `run()` checks `self.stop_requested`.
        pass


class OWParallel(
    OWEwoksWidgetOneThreadPerRun, **ow_build_opts, ewokstaskclass=Parallel
):
    name = "test_OW"


def test_owwidget_parallel(qtbot):
    """Test parallel task execution."""
    widget = OWParallel()

    sleep_seconds = 0.5
    values = [0, 1, 2, 3]
    stops = [False, True, False, False]
    synchronize_run = Barrier(len(values))

    # all jobs start when the last run method is called
    futures = []
    for value, stop in zip(values, stops):
        widget.set_dynamic_input("value", value)
        widget.set_dynamic_input("sleep", sleep_seconds)
        widget.set_dynamic_input("synchronize_run", synchronize_run)
        futures.append(widget.execute_ewoks_task())

    # request some jobs to stop
    for future, stop in zip(futures, stops):
        if stop:
            _ = future.request_stop()

    # check results
    times = []
    for future, value, stop in zip(futures, values, stops):
        if stop:
            with pytest.raises(TaskExecutionError) as exc_info:
                _ = future.result(timeout=10)

            assert future.stop_requested()

            assert isinstance(exc_info.value.__cause__, Stopped)
            assert exc_info.value.__cause__.value == value

            times.append(exc_info.value.__cause__.time)
        else:
            outputs = future.result(timeout=10)

            assert not future.stop_requested()

            assert outputs["value"].value == value
            times.append(outputs["time"].value)

    assert (numpy.diff(times) < 1.5 * sleep_seconds).all(), "not executed in parallel"
