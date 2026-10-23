import threading
import time

import numpy
from ewokscore.task import Task

from ...gui.owwidgets.meta import ow_build_opts
from ...gui.owwidgets.threaded import OWEwoksWidgetOneThread
from ...gui.qt_utils.app import wait_until


class Sequential(
    Task, input_names=["value", "sleep"], output_names=["value", "time", "thread_id"]
):
    def run(self):
        time.sleep(self.inputs.sleep)
        self.outputs.time = time.perf_counter()
        self.outputs.value = self.inputs.value
        self.outputs.thread_id = threading.get_ident()


class OWSequential(OWEwoksWidgetOneThread, **ow_build_opts, ewokstaskclass=Sequential):
    name = "test_OW"


def test_owwidget_drop(qtbot):
    """Test sequential task execution in one worker thread with drop-when-busy."""
    widget = OWSequential()

    sleep_seconds = 0.5
    futures = {}

    def submit(value):
        widget.set_dynamic_input("value", value)
        widget.set_dynamic_input("sleep", sleep_seconds)
        futures[value] = widget.execute_ewoks_task()

    submit(0)
    submit(1)  # busy with 0
    futures[0].result(timeout=10)
    assert wait_until(lambda: not widget.has_pending_task(), timeout=10)
    submit(2)
    submit(3)  # busy with 2
    futures[2].result(timeout=10)

    completed = [v for v, future in futures.items() if future is not None]
    dropped = [v for v, future in futures.items() if future is None]
    assert completed == [0, 2], "not in order"
    assert dropped == [1, 3], "not in order"

    outputs = [futures[v].result(timeout=10) for v in completed]
    times = [output["time"].value for output in outputs]
    in_threads = [
        output["thread_id"].value != threading.get_ident() for output in outputs
    ]

    assert (numpy.diff(times) >= sleep_seconds).all(), "not sequential"
    assert all(in_threads), "in main thread"
