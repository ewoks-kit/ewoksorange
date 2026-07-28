from threading import Lock

from ewokscore.task import Task

from .abstract import TaskController


class ThreadTaskController(TaskController):
    """Controls a task running in another thread.

    The task object lives in the same process, so cancellation is done by
    directly calling task.cancel().
    """

    def __init__(self):
        self._task = None
        self._abort_requested = False
        self._lock = Lock()

    def set_task(self, task: Task) -> None:
        with self._lock:
            self._task = task
            if self._abort_requested:
                task.cancel()

    def abort(self) -> bool:
        with self._lock:
            self._abort_requested = True

            if self._task is None:
                return False

            self._task.cancel()
            return True

    def aborted(self) -> bool:
        with self._lock:
            task = self._task

        return task is not None and task.cancelled
