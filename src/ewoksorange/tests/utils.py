from time import sleep
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


class DummyTask(
    Task,
    input_names=("my_object", "value"),
    optional_input_names=("sleep_duration",),
    output_names=("my_object",),
):
    """Task that set a value to MyObject and set a 'finished' Event"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__cancelled = False

    def run(self):
        sleep(self.get_input_values().get("sleep_duration", 0))
        my_object = self.inputs.my_object

        if self.__cancelled:
            my_object.value = "cancelled"
        else:
            my_object.value = self.inputs.value
        self.outputs.my_object = my_object
        my_object.finished_callback()

    def cancel(self):
        self.__cancelled = True
