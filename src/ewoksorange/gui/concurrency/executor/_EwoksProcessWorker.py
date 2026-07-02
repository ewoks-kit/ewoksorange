from typing import Optional

from ._EwoksWorkerBase import EwoksWorkerBase


class EwoksProcessWorker(EwoksWorkerBase):
    """Controls a task running in a subprocess via multiprocessing.Event objects."""

    def __init__(self, abort_event, aborted_event):
        self._abort_event = abort_event
        self._aborted_event = aborted_event

    def abort(self) -> None:
        self._abort_event.set()

    def aborted(self) -> bool:
        return self._aborted_event.is_set()
