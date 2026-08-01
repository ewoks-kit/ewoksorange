from itertools import combinations
from typing import Tuple

import pytest

from .tasks import TimedTask


def test_parallel_execution(qtapp, executor_context_factory) -> None:
    workers: int = 2
    with executor_context_factory(workers=workers) as (kind, executor, recorder):
        if kind == "sync":
            pytest.skip(f"abort not supported by {kind!r} executor")
            return

        futures = [
            executor.submit_task(TimedTask, inputs={"value": i, "delay": 1})
            for i in range(4)
        ]

        results = [future.result(timeout=10) for future in futures]

        intervals = [(r["start"].value, r["end"].value) for r in results]

        # With 4 tasks and 2 workers, expect two batches of 2 tasks each
        # running at the same time. The exact pair count is timing-sensitive
        # (scheduling jitter can make a 3rd task start early), so only the
        # minimum expected from genuine parallelism is checked.
        overlapping_pairs = sum(_overlaps(a, b) for a, b in combinations(intervals, 2))
        assert overlapping_pairs >= workers

        recorder.wait_for("finished", 4)
        recorder.assert_counts(submitted=4, started=4, succeeded=4, finished=4)


def _overlaps(interval_a: Tuple[float, float], interval_b: Tuple[float, float]) -> bool:
    """Check whether two (start, end) time intervals overlap."""
    start_a, end_a = interval_a
    start_b, end_b = interval_b
    return start_a < end_b and start_b < end_a
