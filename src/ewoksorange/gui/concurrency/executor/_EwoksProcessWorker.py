class EwoksProcessWorker:
    """Controls a task running in a subprocess via a multiprocessing.Event."""

    def __init__(self, abort_event):
        self._abort_event = abort_event

    def abort(self) -> None:
        self._abort_event.set()

    @property
    def has_task(self) -> bool:
        return True
