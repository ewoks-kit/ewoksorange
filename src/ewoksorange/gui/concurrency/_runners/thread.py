import threading
from typing import Any
from typing import Callable
from typing import Dict
from typing import Type

from ewokscore.task import Task

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
        super().__init__(task_class, task_kwargs, controller.abort_event)
        self._controller = controller
        self._ready_event = ready_event
        self._on_about_to_start = on_about_to_start
        self._on_started = on_started

    def _wait_ready(self) -> None:
        self._ready_event.wait()

    def _announce_about_to_start(self) -> None:
        self._on_about_to_start()

    def _announce_started(self, task: Task) -> None:
        self._controller.set_task(task)
        self._on_started()
