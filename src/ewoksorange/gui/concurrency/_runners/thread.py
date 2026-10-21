import threading
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Type

from ewokscore.task import Task
from ewokscore.variable import VariableContainer

from .._controllers.abstract import StartDenial
from .._controllers.thread import ThreadTaskController
from .abstract import TaskRunner


class ThreadTaskRunner(TaskRunner):
    """Runs an ewoks task in a worker thread."""

    def __init__(
        self,
        task_class: Type[Task],
        task_kwargs: Dict[str, Any],
        controller: ThreadTaskController,
        ready_event: threading.Event,
        on_about_to_start: Callable[[], None],
        on_started: Callable[[], None],
    ):
        super().__init__(task_class, task_kwargs)
        self._controller = controller
        self._ready_event = ready_event
        self._on_about_to_start = on_about_to_start
        self._on_started = on_started

    def _wait_ready(self) -> None:
        self._ready_event.wait()

    def _try_start(self) -> Optional[StartDenial]:
        return self._controller.try_start()

    def _announce_about_to_start(self) -> None:
        self._on_about_to_start()

    def _announce_started(self, task: Task) -> None:
        self._on_started()

    def _execute(self, task: Task) -> VariableContainer:
        return self._execute_with_stop_event(task, self._controller.stop_event)
