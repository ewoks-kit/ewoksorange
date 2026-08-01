import time

import pytest

from ...gui.concurrency.executor import SubmitPolicy
from .tasks import AddTask


def test_drop_if_busy(qtapp, executor_context_factory):
    with executor_context_factory(SubmitPolicy.DROP_IF_BUSY, workers=1) as (
        kind,
        executor,
        recorder,
    ):
        if kind == "sync":
            pytest.skip(f"abort not supported by {kind!r} executor")
            return

        first = executor.submit_task(AddTask, inputs={"a": 1, "delay": 2})

        time.sleep(0.1)

        second = executor.submit_task(AddTask, inputs={"a": 2})

        assert first is not None
        assert second is None

        first.result(timeout=10)

        recorder.wait_for("finished", 1)
        recorder.assert_counts(
            submitted=1, ignored=1, started=1, succeeded=1, finished=1
        )


def test_always_queue(qtapp, executor_context_factory):

    with executor_context_factory(SubmitPolicy.ALWAYS, workers=1) as (
        _,
        executor,
        recorder,
    ):
        futures = []

        for i in range(3):
            futures.append(executor.submit_task(AddTask, inputs={"a": i, "delay": 0.2}))

        for future in futures:
            future.result(timeout=10)

        recorder.wait_for("finished", 3)
        recorder.assert_counts(submitted=3, started=3, succeeded=3, finished=3)
