from typing import Any
from typing import Dict
from typing import Type

from ewokscore.task import Task
from ewokscore.variable import VariableContainer

from .._controllers.thread import ThreadTaskController
from .abstract import TaskRunner


class ThreadTaskRunner(TaskRunner):
    """Runs an ewoks task in the executor worker thread.

    The task object stays in the same process. The controller is informed of
    the created task so that abort() can call task.cancel().
    """

    def __init__(
        self,
        task_class: Type[Task],
        task_kwargs: Dict[str, Any],
        controller: ThreadTaskController,
    ):
        super().__init__(task_class, task_kwargs)
        self._controller = controller

    def __call__(self) -> VariableContainer:
        task = self._create_task()
        self._controller.set_task(task)
        return self._execute(task)
