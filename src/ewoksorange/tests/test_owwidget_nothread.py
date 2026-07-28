import threading
import time

import numpy
from ewokscore.task import Task

from ..gui.owwidgets.meta import ow_build_opts
from ..gui.owwidgets.nothread import OWEwoksWidgetNoThread


class Sequential(
    Task, input_names=["value", "sleep"], output_names=["value", "time", "thread_id"]
):
    def run(self):
        time.sleep(self.inputs.sleep)
        self.outputs.time = time.perf_counter()
        self.outputs.value = self.inputs.value
        self.outputs.thread_id = threading.get_ident()


class OWSequential(OWEwoksWidgetNoThread, **ow_build_opts, ewokstaskclass=Sequential):
    name = "test_OW"


def test_owwidget_nothread(qtapp):
    """Test sequential execution in the calling thread."""
    widget = OWSequential()

    sleep_seconds = 0.5
    values = [0, 1, 2]
    main_thread = threading.get_ident()

    futures = []
    for value in values:
        widget.set_dynamic_input("value", value)
        widget.set_dynamic_input("sleep", sleep_seconds)
        futures.append(widget.execute_ewoks_task())

    results = {}
    thread_ids = {}

    for future in futures:
        outputs = future.result(timeout=10)
        value = outputs["value"].value
        results[value] = outputs["time"].value
        thread_ids[value] = outputs["thread_id"].value

    times = [results[v] for v in values]
    in_main = [thread_ids[v] == main_thread for v in values]

    assert times == sorted(times), "not in order"
    assert (numpy.diff(times) >= sleep_seconds).all(), "not sequential"
    assert all(in_main), "not in main thread"
