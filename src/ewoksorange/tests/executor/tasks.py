import time

from ewokscore.task import Task


class CustomFailure(Exception):
    pass


class CustomCancelled(Exception):
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
                if self.cancelled:
                    raise CustomCancelled(f"cancelled after {(i + 1) * period} seconds")

        if self.inputs.fail:
            raise CustomFailure("intentional failure")

        result = self.inputs.a

        if self.inputs.b:
            result += self.inputs.b

        self.outputs.result = result

    def cancel(self):
        """Interpretation #2: self.cancelled is the request not the state."""
        self.cancelled = True


class RequestCancelTask(
    Task,
    input_names=["duration"],
    output_names=["result"],
):
    """Exits early on cancel, leaving its output undefined."""

    def run(self):
        step = 0.05
        elapsed = 0.0
        while elapsed < self.inputs.duration:
            if self.cancelled:
                return
            time.sleep(step)
            elapsed += step
        self.outputs.result = f"slept {elapsed:.2f}s"

    def cancel(self):
        """Interpretation #2: self.cancelled is the request not the state."""
        self.cancelled = True


class PartialCancelTask(
    Task,
    input_names=["duration"],
    output_names=["first", "second"],
):
    """Sets `first`, then may be cancelled before setting `second`."""

    def run(self):
        self.outputs.first = "first done"

        step = 0.05
        elapsed = 0.0
        while elapsed < self.inputs.duration:
            if self.cancelled:
                return
            time.sleep(step)
            elapsed += step

        self.outputs.second = "second done"

    def cancel(self):
        """Interpretation #2: self.cancelled is the request not the state."""
        self.cancelled = True


class IgnoreCancelTask(
    Task,
    input_names=["duration"],
    output_names=["result"],
):
    """Never checks `self.cancelled`; always completes fully despite cancel()."""

    def run(self):
        time.sleep(self.inputs.duration)
        self.outputs.result = "completed despite abort"

    def cancel(self):
        """Interpretation #2: self.cancelled is the request not the state."""
        self.cancelled = True


class StateCancelTask(
    Task,
    input_names=["duration"],
    output_names=["result"],
):
    """cancel() only records a request; run() itself sets `self.cancelled`
    once stopped."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__cancel_requested = False

    def run(self):
        step = 0.05
        elapsed = 0.0
        while elapsed < self.inputs.duration:
            if self.__cancel_requested:
                self.cancelled = True
                return
            time.sleep(step)
            elapsed += step
        self.outputs.result = f"slept {elapsed:.2f}s"

    def cancel(self):
        """Interpretation #1: self.cancelled is the state not the request."""
        self.__cancel_requested = True


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
