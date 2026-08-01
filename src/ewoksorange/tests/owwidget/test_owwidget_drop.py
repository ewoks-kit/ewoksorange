import threading
import time

import numpy
from ewokscore.task import Task

from ...gui.owwidgets.meta import ow_build_opts
from ...gui.owwidgets.threaded import OWEwoksWidgetOneThread


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


def test_owwidget_drop(qtapp):
    """Test sequential task execution in one worker thread with drop-when-busy."""
    widget = OWSequential()

    sleep_seconds = 0.5
    values = [0, 1, 2, 3]

    futures = []
    for value in values:
        widget.set_dynamic_input("value", value)
        widget.set_dynamic_input("sleep", sleep_seconds)
        futures.append(widget.execute_ewoks_task())
        time.sleep(sleep_seconds * 0.6)

    results = {}
    thread_ids = {}

    for future, value in zip(futures, values):
        if future is None:
            results[value] = None
            thread_ids[value] = None
        else:
            outputs = future.result(timeout=10)
            value = outputs["value"].value
            results[value] = outputs["time"].value
            thread_ids[value] = outputs["thread_id"].value

    completed = [v for v in values if results[v] is not None]
    dropped = [v for v in values if results[v] is None]
    times = [results[v] for v in completed]
    in_threads = [thread_ids[v] != threading.get_ident() for v in completed]

    assert completed == [0, 2], "not in order"
    assert dropped == [1, 3], "not in order"
    assert (numpy.diff(times) >= sleep_seconds).all(), "not sequential"
    assert all(in_threads), "in main thread"
