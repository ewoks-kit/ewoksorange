from ._EwoksWorkerBase import EwoksWorkerBase


class CompletedWorker(EwoksWorkerBase):
    """No-op worker for an already-finished synchronous task."""

    def abort(self) -> None:
        # no abortion possible. We expect the Worker to be created once the task is completed.
        pass

    def aborted(self) -> bool:
        return False
