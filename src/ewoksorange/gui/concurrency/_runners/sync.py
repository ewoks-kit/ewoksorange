from typing import Any
from typing import Callable
from typing import Dict
from typing import Type

from ewokscore.task import Task

from .._controllers.sync import SyncTaskController
from .abstract import TaskRunner


class SyncTaskRunner(TaskRunner):
    """Runs an ewoks task immediately on the calling thread."""

    def __init__(
        self,
        task_class: Type[Task],
        task_kwargs: Dict[str, Any],
        controller: SyncTaskController,
        on_started: Callable[[], None],
    ):
        super().__init__(task_class, task_kwargs, controller.abort_event)
        self._controller = controller
        self._on_started = on_started

    def _announce_started(self, task: Task) -> None:
        self._controller.set_task(task)
        self._on_started()
