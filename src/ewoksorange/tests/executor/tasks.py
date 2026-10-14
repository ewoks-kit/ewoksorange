import os
import threading
import time

from ewokscore import TaskWithProgress
from ewokscore.task import Task


class CustomFailure(Exception):
    pass


class CustomStopped(Exception):
    pass


class AddTask(
    Task,
    input_names=["a"],
    optional_input_names=["b", "delay", "fail"],
    output_names=["result"],
):
    def run(self):
        if self.inputs.delay:
            period = self.inputs.delay / 40
            for i in range(40):
                time.sleep(period)
                if self.stop_requested:
                    raise CustomStopped(f"stopped after {(i + 1) * period} seconds")

        if self.inputs.fail:
            raise CustomFailure("intentional failure")

        result = self.inputs.a

        if self.inputs.b:
            result += self.inputs.b

        self.outputs.result = result

    def _on_stop_requested(self):
        """Nothing to do: `run()` polls `self.stop_requested`."""
        pass


class EarlyStopTask(
    Task,
    input_names=["duration"],
    output_names=["result"],
):
    """Exits early on a stop request, leaving its output undefined."""

    def run(self):
        step = 0.05
        elapsed = 0.0
        while elapsed < self.inputs.duration:
            if self.stop_requested:
                return
            time.sleep(step)
            elapsed += step
        self.outputs.result = f"slept {elapsed:.2f}s"

    def _on_stop_requested(self):
        """Nothing to do: `run()` polls `self.stop_requested`."""
        pass


class PartialStopTask(
    Task,
    input_names=["duration"],
    output_names=["first", "second"],
):
    """Sets `first`, then may be requested to stop before setting `second`."""

    def run(self):
        self.outputs.first = "first done"

        step = 0.05
        elapsed = 0.0
        while elapsed < self.inputs.duration:
            if self.stop_requested:
                return
            time.sleep(step)
            elapsed += step

        self.outputs.second = "second done"

    def _on_stop_requested(self):
        """Nothing to do: `run()` polls `self.stop_requested`."""
        pass


class IgnoreStopTask(
    Task,
    input_names=["duration"],
    output_names=["result"],
):
    """Never checks `self.stop_requested`; always completes fully despite request_stop()."""

    def run(self):
        time.sleep(self.inputs.duration)
        self.outputs.result = "completed despite stop request"

    def _on_stop_requested(self):
        """Nothing to do: `run()` polls `self.stop_requested`."""
        pass


class CleanupTask(
    Task,
    input_names=["duration", "marker"],
    output_names=["result"],
):
    """Never checks `self.stop_requested` and creates the file `marker` however it exits."""

    def run(self):
        try:
            end = time.monotonic() + self.inputs.duration
            while time.monotonic() < end:
                time.sleep(0.01)
            self.outputs.result = "completed"
        finally:
            with open(self.inputs.marker, "w"):
                pass


class InterruptStopTask(
    Task,
    input_names=["duration"],
    output_names=["result"],
):
    """Never polls `self.stop_requested`; `_on_stop_requested()` interrupts
    the blocking wait of run() instead."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__stop_event = threading.Event()

    def run(self):
        if self.__stop_event.wait(timeout=self.inputs.duration):
            return
        self.outputs.result = f"slept {self.inputs.duration:.2f}s"

    def _on_stop_requested(self):
        self.__stop_event.set()


class TimedTask(
    Task,
    input_names=["value", "delay"],
    output_names=["value", "start", "end"],
):
    """Sleeps for `delay` seconds, recording the wall-clock interval it ran in.

    Used to verify that tasks actually overlap in time, rather than relying
    on a flaky total-elapsed-time budget.
    """

    def run(self) -> None:
        start = time.monotonic()
        time.sleep(self.inputs.delay)
        self.outputs.start = start
        self.outputs.end = time.monotonic()
        self.outputs.value = self.inputs.value


class ProgressTask(
    TaskWithProgress,
    input_names=["percentages"],
    output_names=["pid"],
):
    """Reports each of `percentages` as task progress.

    Also outputs the pid it ran in, so tests can tell the execution backends
    apart.
    """

    def run(self) -> None:
        for percentage in self.inputs.percentages:
            self.progress = percentage
        self.outputs.pid = os.getpid()


class PidTask(Task, input_names=["value"], output_names=["value", "pid"]):
    """Outputs the pid it ran in. Not a `TaskWithProgress`."""

    def run(self) -> None:
        self.outputs.value = self.inputs.value
        self.outputs.pid = os.getpid()
