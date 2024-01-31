import pytest
from ewokscore.task import Task
from ewokscore.task import TaskInputError

from .utils import execute_task
from ..bindings import owwidgets
from ..bindings import ow_build_opts


class TaskForTesting(Task, input_names=["a", "b"], output_names=["sum"]):

    def run(self):
        self.outputs.sum = self.inputs.a + self.inputs.b


class NoThreadTestWidget(
    owwidgets.OWEwoksWidgetNoThread, **ow_build_opts, ewokstaskclass=TaskForTesting
):
    name = "TaskForTesting"


class OneThreadTestWidget(
    owwidgets.OWEwoksWidgetOneThread, **ow_build_opts, ewokstaskclass=TaskForTesting
):
    name = "TaskForTesting"


class OneThreadPerRunTestWidget(
    owwidgets.OWEwoksWidgetOneThreadPerRun,
    **ow_build_opts,
    ewokstaskclass=TaskForTesting
):
    name = "TaskForTesting"


class TaskStackTestWidget(
    owwidgets.OWEwoksWidgetWithTaskStack, **ow_build_opts, ewokstaskclass=TaskForTesting
):
    name = "TaskForTesting"


class NoThreadTestWidgetCbFailure(
    owwidgets.OWEwoksWidgetNoThread, **ow_build_opts, ewokstaskclass=TaskForTesting
):
    name = "TaskForTesting"

    def task_output_changed(self) -> None:
        assert False, "output changed callback failure"


class OneThreadTestWidgetCbFailure(
    owwidgets.OWEwoksWidgetOneThread, **ow_build_opts, ewokstaskclass=TaskForTesting
):
    name = "TaskForTesting"

    def task_output_changed(self) -> None:
        assert False, "output changed callback failure"


class OneThreadPerRunTestWidgetCbFailure(
    owwidgets.OWEwoksWidgetOneThreadPerRun,
    **ow_build_opts,
    ewokstaskclass=TaskForTesting
):
    name = "TaskForTesting"

    def task_output_changed(self) -> None:
        assert False, "output changed callback failure"


class TaskStackTestWidgetCbFailure(
    owwidgets.OWEwoksWidgetWithTaskStack, **ow_build_opts, ewokstaskclass=TaskForTesting
):
    name = "TaskForTesting"

    def task_output_changed(self) -> None:
        assert False, "output changed callback failure"


class NoThreadTestWidgetPropagateFailure(
    owwidgets.OWEwoksWidgetNoThread, **ow_build_opts, ewokstaskclass=TaskForTesting
):
    name = "TaskForTesting"

    def propagate_downstream(self, **_) -> None:
        assert False, "propagate downstream failure"


class OneThreadTestWidgetPropagateFailure(
    owwidgets.OWEwoksWidgetOneThread, **ow_build_opts, ewokstaskclass=TaskForTesting
):
    name = "TaskForTesting"

    def task_output_changed(self) -> None:
        assert False, "propagate downstream failure"


class OneThreadPerRunTestWidgetPropagateFailure(
    owwidgets.OWEwoksWidgetOneThreadPerRun,
    **ow_build_opts,
    ewokstaskclass=TaskForTesting
):
    name = "TaskForTesting"

    def task_output_changed(self) -> None:
        assert False, "propagate downstream failure"


class TaskStackTestWidgetPropagateFailure(
    owwidgets.OWEwoksWidgetWithTaskStack, **ow_build_opts, ewokstaskclass=TaskForTesting
):
    name = "TaskForTesting"

    def task_output_changed(self) -> None:
        assert False, "propagate downstream failure"


_TASK_CLASSES = [
    TaskForTesting,
    NoThreadTestWidget,
    OneThreadTestWidget,
    OneThreadPerRunTestWidget,
    TaskStackTestWidget,
]

_TASK_CLASSES_CBFAILURE = [
    NoThreadTestWidgetCbFailure,
    OneThreadTestWidgetCbFailure,
    OneThreadPerRunTestWidgetCbFailure,
    TaskStackTestWidgetCbFailure,
]

_TASK_CLASSES_PROPFAILURE = [
    NoThreadTestWidgetPropagateFailure,
    OneThreadTestWidgetPropagateFailure,
    OneThreadPerRunTestWidgetPropagateFailure,
    TaskStackTestWidgetPropagateFailure,
]


@pytest.mark.parametrize("task_cls", _TASK_CLASSES)
def test_execute_task_success(task_cls):
    result = execute_task(task_cls, inputs={"a": 1, "b": 2}, timeout=10)
    assert result == {"sum": 3}


@pytest.mark.parametrize("task_cls", _TASK_CLASSES)
def test_execute_task_failure(task_cls):
    with pytest.raises(TaskInputError):
        execute_task(task_cls, inputs={"a": 1}, timeout=10)


@pytest.mark.parametrize("task_cls", _TASK_CLASSES_CBFAILURE)
def test_execute_output_changed_failure(task_cls):
    with pytest.raises(AssertionError, match="output changed callback failure"):
        execute_task(task_cls, inputs={"a": 1, "b": 2}, timeout=10)


@pytest.mark.parametrize("task_cls", _TASK_CLASSES_PROPFAILURE)
def test_execute_propagate_downstream_failure(task_cls):
    with pytest.raises(AssertionError, match="propagate downstream failure"):
        execute_task(task_cls, inputs={"a": 1, "b": 2}, timeout=10)
