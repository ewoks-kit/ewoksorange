import time

import pytest

from .tasks import AddTask


def test_parallel_execution(qtapp, executor_context_factory):
    with executor_context_factory(workers=2) as (kind, executor, recorder):

        if kind == "sync":
            pytest.skip(f"abort not supported by {kind!r} executor")
            return

        futures = []

        start = time.monotonic()

        for i in range(4):
            futures.append(executor.submit_task(AddTask, inputs={"a": i, "delay": 1}))

        for future in futures:
            future.result(timeout=10)

        elapsed = time.monotonic() - start

        # 4 tasks with 2 workers should take ~2 seconds,
        # not ~4 seconds.
        assert elapsed < 3.5

        recorder.wait_for("finished", 4)
        recorder.assert_counts(submitted=4, started=4, succeeded=4, finished=4)
