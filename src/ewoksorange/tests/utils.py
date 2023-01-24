from typing import List, Mapping, Optional, Union, Type
from ewokscore.task import Task
from ..bindings.owwidgets import OWEwoksBaseWidget
from ..bindings.taskwrapper import execute_ewoks_owwidget


def execute_task(
    task_cls: Union[Type[Task], Type[OWEwoksBaseWidget]],
    inputs: Optional[List[Mapping]] = None,
    timeout: int = 60,
) -> dict:
    """Execute the task (use the orange widget or ewoks task class) and return the results"""
    if issubclass(task_cls, OWEwoksBaseWidget):
        return execute_ewoks_owwidget(task_cls, inputs=inputs, timeout=timeout)
    if issubclass(task_cls, Task):
        task = task_cls(inputs=inputs)
        task.execute()
        return task.output_values
    raise TypeError("task")
