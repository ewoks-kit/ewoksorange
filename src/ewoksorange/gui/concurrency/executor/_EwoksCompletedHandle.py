from ._EwoksTaskHandle import EwoksTaskHandle as _EwoksTaskHandle


class EwoksCompletedHandle(_EwoksTaskHandle):
    """No-op handler for an already-finished synchronous task."""

    def abort(self) -> None:
        # no abortion possible. We expect the Worker to be created once the task is completed.
        pass

    def aborted(self) -> bool:
        return False
