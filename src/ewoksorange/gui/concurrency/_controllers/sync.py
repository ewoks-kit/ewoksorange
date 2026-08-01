from .abstract import TaskController


class SyncTaskController(TaskController):
    """Controller for a task that already finished.

    Used for synchronous execution where abort is impossible because the task
    has already returned.
    """

    def abort(self) -> bool:
        return False

    def aborted(self) -> bool:
        return False
