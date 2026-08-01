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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__cancelled = False

    def run(self):
        if self.inputs.delay:
            period = self.inputs.delay / 40
            for i in range(40):
                time.sleep(period)
                if self.__cancelled:
                    raise CustomCancelled(f"cancelled after {(i + 1) * period} seconds")

        if self.inputs.fail:
            raise CustomFailure("intentional failure")

        result = self.inputs.a

        if self.inputs.b:
            result += self.inputs.b

        self.outputs.result = result

    def cancel(self):
        self.__cancelled = True


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
