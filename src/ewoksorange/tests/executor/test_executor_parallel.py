import threading
import time
from itertools import combinations
from typing import Tuple

from .tasks import PidTask
from .tasks import TimedTask
from .utils import assert_signal_counts


def test_parallel_execution(qtbot, executor_context_factory) -> None:
    workers: int = 2
    with executor_context_factory(workers=workers) as (kind, executor):
        if kind == "process":
            _warmup_workers(qtbot, executor, workers)

        inputs_list = [{"value": i, "delay": 1} for i in range(4)]
        futures = [None] * len(inputs_list)

        def _submit(index: int, inputs: dict) -> None:
            futures[index] = executor.submit_task(TimedTask, inputs=inputs)

        threads = [
            threading.Thread(target=_submit, args=(index, inputs))
            for index, inputs in enumerate(inputs_list)
        ]
        n = len(threads)
        with assert_signal_counts(
            qtbot,
            executor,
            submitted=n,
            aboutToStart=n,
            started=n,
            succeeded=n,
            finished=n,
        ):
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)

            results = [future.result(timeout=10) for future in futures]

        # Concurrency must not corrupt individual results.
        assert [r["value"].value for r in results] == list(range(4))

        intervals = [(r["start"].value, r["end"].value) for r in results]

        # With 4 tasks and 2 workers, expect two batches of 2 tasks each
        # running at the same time. The exact pair count is timing-sensitive
        # (scheduling jitter can make a 3rd task start early), so only the
        # minimum expected from genuine parallelism is checked.
        overlapping_pairs = sum(_overlaps(a, b) for a, b in combinations(intervals, 2))
        assert overlapping_pairs >= workers


def _warmup_workers(qtbot, executor, workers: int, timeout: float = 60) -> None:
    """Wait until all workers executed a task, since subprocess workers can become
    ready at very different times. Returns once all their signals were received."""
    pids = set()
    t0 = time.monotonic()
    while len(pids) < workers:
        assert time.monotonic() - t0 < timeout, "not all workers became ready"
        with qtbot.wait_signals(
            [executor.finished] * workers, timeout=int(timeout * 1000)
        ):
            futures = [
                executor.submit_task(PidTask, inputs={"value": 0})
                for _ in range(workers)
            ]
            pids.update(
                future.result(timeout=timeout)["pid"].value for future in futures
            )


def _overlaps(interval_a: Tuple[float, float], interval_b: Tuple[float, float]) -> bool:
    """Check whether two (start, end) time intervals overlap."""
    start_a, end_a = interval_a
    start_b, end_b = interval_b
    return start_a < end_b and start_b < end_a
