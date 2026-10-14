from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Type

from ewokscore.task import Task
from ewokscore.variable import VariableContainer

from .._controllers.abstract import StartDenial
from .._controllers.sync import SyncTaskController
from .abstract import TaskRunner


class SyncTaskRunner(TaskRunner):
    """Runs an ewoks task immediately on the calling thread."""

    def __init__(
        self,
        task_class: Type[Task],
        task_kwargs: Dict[str, Any],
        controller: SyncTaskController,
        on_about_to_start: Callable[[], None],
        on_started: Callable[[], None],
    ):
        super().__init__(task_class, task_kwargs)
        self._controller = controller
        self._on_about_to_start = on_about_to_start
        self._on_started = on_started

    def _try_start(self) -> Optional[StartDenial]:
        return self._controller.try_start()

    def _announce_about_to_start(self) -> None:
        self._on_about_to_start()

    def _announce_started(self, task: Task) -> None:
        self._on_started()

    def _execute(self, task: Task) -> VariableContainer:
        return self._execute_with_stop_event(task, self._controller.stop_event)
