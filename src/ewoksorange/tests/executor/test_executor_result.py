import pytest
from ewoksutils.exceptions import TaskExecutionError

from .tasks import AddTask


def test_success(qtapp, executor_context_factory):
    with executor_context_factory() as (_, executor, recorder):

        future = executor.submit_task(AddTask, inputs={"a": 10, "b": 5})

        result = future.result(timeout=10)

        assert result["result"].value == 15

        recorder.wait_for("finished", 1)

        recorder.assert_counts(submitted=1, started=1, succeeded=1, finished=1)
        recorder.assert_order("submitted", "started", "succeeded", "finished")
        recorder.assert_started(future)
        recorder.assert_finished(future)
        recorder.assert_succeeded(future, result)


def test_failure(qtapp, executor_context_factory):

    with executor_context_factory() as (_, executor, recorder):

        future = executor.submit_task(AddTask, inputs={"a": 1, "fail": True})

        match = "intentional failure"
        with pytest.raises(TaskExecutionError, match=match):
            _ = future.result(timeout=10)

        recorder.wait_for("finished", 1)
        recorder.assert_counts(submitted=1, started=1, failed=1, finished=1)
        recorder.assert_order("submitted", "started", "failed", "finished")
        recorder.assert_failed(future, TaskExecutionError, match=match)
