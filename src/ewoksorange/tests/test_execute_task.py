from typing import Dict
from typing import List

import pytest
from ewokscore.task import Task
from ewokscore.task import TaskInputError

from ..gui.owwidgets.meta import ow_build_opts
from ..gui.owwidgets.nothread import OWEwoksWidgetNoThread
from ..gui.owwidgets.threaded import OWEwoksWidgetOneThread
from ..gui.owwidgets.threaded import OWEwoksWidgetOneThreadPerRun
from ..gui.owwidgets.threaded import OWEwoksWidgetWithTaskStack
from .utils import execute_task


class TaskForTesting(
    Task, input_names=["a", "b", "recorded_calls", "failures"], output_names=["sum"]
):
    def run(self):
        self.inputs.recorded_calls.append("run")
        exception = self.inputs.failures.get("run")
        if exception:
            raise exception
        self.outputs.sum = self.inputs.a + self.inputs.b


class PatchCalls:
    def __init__(
        self, *args, recorded_calls: List[str], failures: Dict[str, Exception], **kw
    ) -> None:
        self.__recorded_calls = recorded_calls
        self.__failures = failures
        super().__init__(*args, **kw)

    def task_output_changed(self) -> None:
        self.__recorded_calls.append("task_output_changed")
        super().task_output_changed()
        exception = self.__failures.get("task_output_changed")
        if exception:
            raise exception

    def trigger_downstream(self) -> None:
        self.__recorded_calls.append("trigger_downstream")
        super().trigger_downstream()
        exception = self.__failures.get("trigger_downstream")
        if exception:
            raise exception

    def clear_downstream(self) -> None:
        self.__recorded_calls.append("clear_downstream")
        super().clear_downstream()
        exception = self.__failures.get("clear_downstream")
        if exception:
            raise exception


class NoThreadTestWidget(
    PatchCalls,
    OWEwoksWidgetNoThread,
    **ow_build_opts,
    ewokstaskclass=TaskForTesting,
):
    name = "TaskForTesting"


class OneThreadTestWidget(
    PatchCalls,
    OWEwoksWidgetOneThread,
    **ow_build_opts,
    ewokstaskclass=TaskForTesting,
):
    name = "TaskForTesting"


class OneThreadPerRunTestWidget(
    PatchCalls,
    OWEwoksWidgetOneThreadPerRun,
    **ow_build_opts,
    ewokstaskclass=TaskForTesting,
):
    name = "TaskForTesting"


class TaskStackTestWidget(
    PatchCalls,
    OWEwoksWidgetWithTaskStack,
    **ow_build_opts,
    ewokstaskclass=TaskForTesting,
):
    name = "TaskForTesting"


_TASK_CLASSES = [TaskForTesting]

_WIDGET_CLASSES = [
    NoThreadTestWidget,
    OneThreadTestWidget,
    OneThreadPerRunTestWidget,
    TaskStackTestWidget,
]


class _TestException(Exception):
    pass


@pytest.mark.parametrize("task_cls", _TASK_CLASSES + _WIDGET_CLASSES)
def test_task_success(task_cls):
    recorded_calls = list()
    failures = dict()
    result = _execute_task(task_cls, recorded_calls, failures, a=1, b=2)
    assert result == {"sum": 3}
    if issubclass(task_cls, Task):
        assert recorded_calls == ["run"]
    else:
        assert recorded_calls == ["run", "trigger_downstream", "task_output_changed"]


@pytest.mark.parametrize("task_cls", _TASK_CLASSES + _WIDGET_CLASSES)
def test_task_init_failure(task_cls):
    recorded_calls = list()
    failures = dict()
    with pytest.raises(TaskInputError):
        _execute_task(task_cls, recorded_calls, failures, a=1)
    if issubclass(task_cls, Task):
        assert recorded_calls == []
    else:
        assert recorded_calls == ["clear_downstream", "task_output_changed"]


@pytest.mark.parametrize("task_cls", _TASK_CLASSES + _WIDGET_CLASSES)
def test_task_run_failure(task_cls):
    recorded_calls = list()
    failures = {"run": _TestException("error in task")}

    if issubclass(task_cls, Task):
        with pytest.raises(RuntimeError) as exc_info:
            _execute_task(task_cls, recorded_calls, failures, a=1, b=2)
        exception = exc_info.value.__cause__
        assert isinstance(exception, _TestException)
        assert str(exception) == "error in task"
        assert recorded_calls == ["run"]
    else:
        with pytest.raises(_TestException, match="error in task") as exc_info:
            _execute_task(task_cls, recorded_calls, failures, a=1, b=2)
        assert recorded_calls == ["run", "clear_downstream", "task_output_changed"]


@pytest.mark.parametrize("task_cls", _WIDGET_CLASSES)
def test_success_with_output_changed_failure(task_cls):
    recorded_calls = list()
    failures = {
        "task_output_changed": _TestException("error in widget: output callback")
    }

    with pytest.raises(_TestException, match="error in widget: output callback"):
        _execute_task(task_cls, recorded_calls, failures, a=1, b=2)
    assert recorded_calls == ["run", "trigger_downstream", "task_output_changed"]


@pytest.mark.parametrize("task_cls", _WIDGET_CLASSES)
def test_failure_with_output_changed_failure(task_cls):
    recorded_calls = list()
    failures = {
        "run": _TestException("error in task"),
        "task_output_changed": _TestException("error in widget: output callback"),
    }

    with pytest.raises(_TestException, match="error in task"):
        _execute_task(task_cls, recorded_calls, failures, a=1, b=2)
    assert recorded_calls == ["run", "clear_downstream", "task_output_changed"]


@pytest.mark.parametrize("task_cls", _WIDGET_CLASSES)
def test_success_with_propagation_failure(task_cls):
    recorded_calls = list()
    failures = {
        "trigger_downstream": _TestException("error in widget: success propagation")
    }

    with pytest.raises(_TestException, match="error in widget: success propagation"):
        _execute_task(task_cls, recorded_calls, failures, a=1, b=2)
    assert recorded_calls == ["run", "trigger_downstream", "task_output_changed"]


@pytest.mark.parametrize("task_cls", _WIDGET_CLASSES)
def test_failure_with_propagation_failure(task_cls):
    recorded_calls = list()
    failures = {
        "run": _TestException("error in task"),
        "clear_downstream": _TestException("error in widget: failure propagation"),
    }

    with pytest.raises(_TestException, match="error in task"):
        _execute_task(task_cls, recorded_calls, failures, a=1, b=2)
    assert recorded_calls == ["run", "clear_downstream", "task_output_changed"]


@pytest.mark.parametrize("task_cls", _WIDGET_CLASSES)
def test_success_with_propagation_and_output_changed_failure(task_cls):
    recorded_calls = list()
    failures = {
        "trigger_downstream": _TestException("error in widget: success propagation"),
        "task_output_changed": _TestException("error in widget: output callback"),
    }

    with pytest.raises(_TestException, match="error in widget: output callback"):
        _execute_task(task_cls, recorded_calls, failures, a=1, b=2)
    assert recorded_calls == ["run", "trigger_downstream", "task_output_changed"]


@pytest.mark.parametrize("task_cls", _WIDGET_CLASSES)
def test_failure_with_propagation_and_output_changed_failure(task_cls):
    recorded_calls = list()
    failures = {
        "run": _TestException("error in task"),
        "clear_downstream": _TestException("error in widget: success propagation"),
        "task_output_changed": _TestException("error in widget: output callback"),
    }

    with pytest.raises(_TestException, match="error in task"):
        _execute_task(task_cls, recorded_calls, failures, a=1, b=2)
    assert recorded_calls == ["run", "clear_downstream", "task_output_changed"]


def _execute_task(
    task_cls, recorded_calls: List[str], failures: Dict[str, Exception], **params
) -> dict:
    return execute_task(
        task_cls,
        inputs={**params, "recorded_calls": recorded_calls, "failures": failures},
        timeout=10,
        recorded_calls=recorded_calls,
        failures=failures,
    )
