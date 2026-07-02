class EwoksWorkerBase:
    """Common interface for objects that control a running ewoks task."""

    def abort(self) -> None:
        """Abort the running ewoks task."""
        raise NotImplementedError("Base class")

    def aborted(self) -> bool:
        """Return True if the task was aborted."""
        raise NotImplementedError("Base class")
