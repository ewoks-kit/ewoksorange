import pytest
from ewoksutils.exceptions import TaskExecutionError

from .tasks import AddTask
from .utils import assert_exception


def test_success(qtbot, executor_context_factory):
    with executor_context_factory() as (_, executor):
        with qtbot.wait_signals(
            (
                executor.submitted,
                executor.started,
                executor.succeeded,
                executor.finished,
            ),
            timeout=15_000,
            order="strict",
        ) as signals_blocker:
            future = executor.submit_task(AddTask, inputs={"a": 10, "b": 5})

            result = future.result(timeout=10)

            assert result["result"].value == 15

        received_futures = [
            item.args[0] for item in signals_blocker.all_signals_and_args
        ]
        assert all(future is received for received in received_futures)


def test_failure(qtbot, executor_context_factory):

    with executor_context_factory() as (_, executor):
        with qtbot.wait_signals(
            (executor.submitted, executor.started, executor.failed, executor.finished),
            timeout=15_000,
            order="strict",
        ):
            future = executor.submit_task(AddTask, inputs={"a": 1, "fail": True})

            match = "intentional failure"
            with pytest.raises(TaskExecutionError, match=match):
                _ = future.result(timeout=10)

        assert_exception(future.exception(), TaskExecutionError, match=match)
