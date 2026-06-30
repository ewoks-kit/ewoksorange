class CompletedWorker:
    """No-op worker for an already-finished synchronous task."""

    def abort(self) -> None:
        # no abortion possible. We expect the Worker to be created once the task is completed.
        pass

    @property
    def has_task(self) -> bool:
        return False
