from multiprocessing.synchronize import Event

from .abstract import TaskController


class ProcessTaskController(TaskController):
    """Controls a task running in another process.

    Communication with the child process happens through multiprocessing
    Event proxies.
    """

    def __init__(
        self,
        abort_event: Event,
        aborted_event: Event,
    ):
        self._abort_event = abort_event
        self._aborted_event = aborted_event

    def abort(self) -> bool:
        self._abort_event.set()
        return True

    def aborted(self) -> bool:
        return self._aborted_event.is_set()
