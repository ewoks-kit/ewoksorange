from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import Type

from ewokscore import TaskWithProgress
from ewokscore.task import Task
from ewokscore.variable import VariableContainer


class TaskRunner(ABC):
    """Base class for ewoks task execution runners."""

    def __init__(
        self,
        task_class: Type[Task],
        task_kwargs: Dict[str, Any],
    ):
        self._task_class = task_class
        self._task_kwargs = task_kwargs

    def _create_task(self) -> Task:
        kwargs = dict(self._task_kwargs)

        if not issubclass(self._task_class, TaskWithProgress):
            kwargs.pop("progress", None)

        return self._task_class(**kwargs)

    def _execute(self, task: Task) -> VariableContainer:
        task.execute(raise_on_error=True)
        return task.output_variables

    @abstractmethod
    def __call__(self) -> VariableContainer:
        raise NotImplementedError
