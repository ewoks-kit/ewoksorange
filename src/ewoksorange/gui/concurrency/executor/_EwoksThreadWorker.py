from threading import Lock
from typing import Optional
from typing import Type

from ewokscore import TaskWithProgress
from ewokscore.task import Task

from ._EwoksWorkerBase import EwoksWorkerBase


class EwoksThreadWorker(EwoksWorkerBase):
    """Callable that instantiates and executes an ewoks task in the worker thread."""

    def __init__(self, task_class: Type[Task], **task_kwargs):
        self._task_class = task_class
        self._task_kwargs = task_kwargs
        self._task: Optional[Task] = None
        self._lock = Lock()

    def __call__(self):
        task_class = self._task_class
        kwargs = dict(self._task_kwargs)
        if not issubclass(task_class, TaskWithProgress):
            kwargs.pop("progress", None)

        task = task_class(**kwargs)
        with self._lock:
            self._task = task

        try:
            task.execute()
        except Exception as exc:
            # ewokscore wraps run() exceptions in RuntimeError; re-raise the
            # original so callers see the same type as the nothread path.
            original = task.exception
            raise original if original is not None else exc
        return task.output_variables

    def abort(self) -> bool:
        """Call the ewoks task's cancel() to stop a running task. Returns True if the task was reached."""
        with self._lock:
            task = self._task
            if task is not None:
                task.cancel()
                return True
            return False

    def aborted(self) -> bool:
        with self._lock:
            task = self._task
        return task is not None and task.cancelled
