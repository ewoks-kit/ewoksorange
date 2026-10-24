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


class WaitForFileTask(
    Task,
    input_names=["path"],
    output_names=["result"],
):
    """Never checks `self.stop_requested` and completes once the file `path` exists."""

    def run(self):
        end = time.monotonic() + 30
        while not os.path.exists(self.inputs.path):
            if time.monotonic() > end:
                raise TimeoutError(f"{self.inputs.path} does not exist")
            time.sleep(0.01)
        self.outputs.result = "completed despite stop request"

    def _on_stop_requested(self):
        """Nothing to do: the stop request is ignored."""
        pass


class SurviveAbortTask(
    Task,
    input_names=["duration", "marker"],
    output_names=["result"],
):
    """Never checks `self.stop_requested` and survives an abort: creates the file
    `marker` when interrupted, then keeps running."""

    def run(self):
        end = time.monotonic() + self.inputs.duration
        while True:
            try:
                while time.monotonic() < end:
                    time.sleep(0.01)
                break
            except KeyboardInterrupt:
                with open(self.inputs.marker, "w"):
                    pass
        self.outputs.result = "completed"

    def _on_stop_requested(self):
        """Nothing to do: the stop request is ignored."""
        pass


class StartMarkerTask(
    Task,
    input_names=["duration", "marker"],
    output_names=["result"],
):
    """Creates the file `marker` when it starts, then never checks `self.stop_requested`."""

    def run(self):
        with open(self.inputs.marker, "w"):
            pass
        end = time.monotonic() + self.inputs.duration
        while time.monotonic() < end:
            time.sleep(0.01)
        self.outputs.result = "completed"


class SlowInitTask(
    Task,
    input_names=["init_duration", "duration"],
    output_names=["result"],
):
    """Takes `init_duration` seconds to be created, then never checks `self.stop_requested`."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        time.sleep(self.inputs.init_duration)

    def run(self):
        end = time.monotonic() + self.inputs.duration
        while time.monotonic() < end:
            time.sleep(0.01)
        self.outputs.result = "completed"


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


class ProgressLoopTask(
    TaskWithProgress,
    input_names=["duration"],
    output_names=["result"],
):
    """Reports progress continuously for `duration` seconds."""

    def run(self) -> None:
        end = time.monotonic() + self.inputs.duration
        i = 0
        while time.monotonic() < end:
            i += 1
            self.progress = i % 100
            time.sleep(0.0001)
        self.outputs.result = "completed"


class ProgressBurstTask(
    TaskWithProgress,
    input_names=["duration"],
    output_names=["end"],
):
    """Reports progress as fast as it can for `duration` seconds. Outputs the
    wall-clock time it ended."""

    def run(self) -> None:
        end = time.monotonic() + self.inputs.duration
        i = 0
        while time.monotonic() < end:
            i += 1
            self.progress = i % 100
        self.outputs.end = time.time()


class SurviveAbortProgressTask(
    TaskWithProgress,
    input_names=["timeout"],
    output_names=["result"],
):
    """Waits for an abort, survives it and reports up to 100% before it completes."""

    def run(self) -> None:
        end = time.monotonic() + self.inputs.timeout
        try:
            while time.monotonic() < end:
                time.sleep(0.01)
        except KeyboardInterrupt:
            pass
        else:
            raise TimeoutError("not aborted")
        for percentage in range(1, 101):
            self.progress = percentage
        self.outputs.result = "completed"


class InitProgressTask(
    TaskWithProgress,
    input_names=["value"],
    output_names=["value"],
):
    """Reports 50% when it is created and 100% when it runs."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress = 50

    def run(self) -> None:
        self.progress = 100
        self.outputs.value = self.inputs.value


class PidTask(Task, input_names=["value"], output_names=["value", "pid"]):
    """Outputs the pid it ran in. Not a `TaskWithProgress`."""

    def run(self) -> None:
        self.outputs.value = self.inputs.value
        self.outputs.pid = os.getpid()
