import time

import pytest
from ewoksutils.exceptions import TaskExecutionError

from .tasks import AddTask


def test_abort(qtapp, executor_context_factory):
    with executor_context_factory() as (kind, executor, recorder):
        if kind in ("sync", "thread"):
            pytest.skip(f"abort not supported by {kind!r} executor")
            return

        future = executor.submit_task(AddTask, inputs={"a": 1, "b": 2, "delay": 5})

        time.sleep(0.2)

        assert future.abort()

        match = r"cancelled after [\.0-9]+ seconds"
        with pytest.raises(TaskExecutionError, match=match):
            future.result(timeout=10)

        assert future.aborted()

        recorder.wait_for("finished", 1)
        recorder.assert_counts(submitted=1, started=1, aborted=1, failed=1, finished=1)
        recorder.assert_failed(future, TaskExecutionError, match=match)
