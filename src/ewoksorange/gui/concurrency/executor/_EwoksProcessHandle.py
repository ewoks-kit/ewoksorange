import multiprocessing
from ._EwoksTaskHandle import EwoksTaskHandle


class EwoksProcessHandle(EwoksTaskHandle):
    """Controls a task running in a subprocess via multiprocessing.Event objects."""

    def __init__(self, abort_event: multiprocessing.Event, aborted_event: multiprocessing.Event):  # type: ignore
        self._abort_event = abort_event
        self._aborted_event = aborted_event

    def abort(self) -> bool:
        self._abort_event.set()
        return True

    def aborted(self) -> bool:
        return self._aborted_event.is_set()
