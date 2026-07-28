from ewokscore.variable import VariableContainer

from .abstract import TaskRunner


class SyncTaskRunner(TaskRunner):
    """Runs an ewoks task immediately in the calling thread."""

    def __call__(self) -> VariableContainer:
        task = self._create_task()
        return self._execute(task)
