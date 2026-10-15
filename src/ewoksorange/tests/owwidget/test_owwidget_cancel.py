import time

from ewokscore.task import Task

from ...gui.owwidgets.meta import ow_build_opts
from ...gui.owwidgets.threaded import OWEwoksWidgetWithTaskStack
from ...gui.qt_utils.app import wait_until


class Sleep(Task, input_names=["seconds"], output_names=["seconds"]):
    def run(self):
        time.sleep(self.inputs.seconds)
        self.outputs.seconds = self.inputs.seconds


class OWSleep(OWEwoksWidgetWithTaskStack, **ow_build_opts, ewokstaskclass=Sleep):
    name = "test_OW_sleep"


def test_cancelled_task_is_not_pending(ewoksorange_qtapp):
    """A task cancelled before it starts does not stay pending in the widget."""
    widget = OWSleep()
    try:
        widget.set_dynamic_input("seconds", 0.5)
        running = widget.execute_ewoks_task()
        queued = widget.execute_ewoks_task()

        assert queued.cancel()
        running.result(timeout=10)

        assert wait_until(lambda: not widget.has_pending_task(), timeout=10)
    finally:
        widget.onDeleteWidget()
