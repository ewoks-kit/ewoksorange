class CompletedWorker:
    """No-op worker for an already-finished synchronous task."""

    def abort(self) -> None:
        pass

    @property
    def has_task(self) -> bool:
        return False
