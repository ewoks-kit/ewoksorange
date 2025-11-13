from typing import Mapping
from typing import Optional
from typing import Type
from typing import Union

from ewokscore.task import Task

from ..gui.owwidgets.types import OWEwoksBaseWidget
from ..gui.owwidgets.types import is_ewoks_widget_class
from ..gui.owwidgets.types import is_native_widget_class
from ..gui.workflows.task_wrappers import execute_ewoks_owwidget
from ..gui.workflows.task_wrappers import execute_native_owwidget


def execute_task(
    task_cls: Union[Type[Task], Type[OWEwoksBaseWidget]],
    inputs: Optional[Mapping] = None,
    timeout: int = 60,
    **widget_init_params,
) -> dict:
    """Execute the task (use the orange widget or ewoks task class) and return the results"""
    if is_ewoks_widget_class(task_cls):
        return execute_ewoks_owwidget(
            task_cls, inputs=inputs, timeout=timeout, **widget_init_params
        )
    if is_native_widget_class(task_cls):
        return execute_native_owwidget(
            task_cls, inputs=inputs, timeout=timeout, **widget_init_params
        )
    if issubclass(task_cls, Task):
        task = task_cls(inputs=inputs)
        task.execute()
        return task.get_output_values()
    raise TypeError("task")
