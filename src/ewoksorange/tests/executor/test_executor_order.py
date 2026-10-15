import time
from typing import Callable

import pytest

from ...gui.concurrency.executor import Concurrency
from ...gui.concurrency.executor import EwoksExecutor
from ...gui.concurrency.executor import SubmitPolicy
from ...gui.concurrency.executor import create_pool_executor
from .signals import SignalRecorder
from .tasks import AddTask
from .tasks import StartMarkerTask


def test_completion_after_start_while_gui_thread_busy(
    ewoksorange_qtapp, executor_context_factory
):
    """The completion signals follow the start signals, also when the task
    finishes while the GUI thread does not process its events."""
    with executor_context_factory() as (kind, executor, recorder):
        if kind == "sync":
            pytest.skip("sync execution emits all signals directly")

        future = executor.submit_task(AddTask, inputs={"a": 1})
        _wait_without_events(future.done)
        time.sleep(0.5)  # let the completion handling run in the background

        recorder.wait_for("finished", 1)
        recorder.assert_order(
            "submitted", "aboutToStart", "started", "succeeded", "finished"
        )


def test_kill_completion_after_start(
    ewoksorange_qtapp, executor_context_factory, tmp_path
):
    """The completion signals of a task killed from the GUI thread follow the
    start signals that are still queued for the GUI thread."""
    with executor_context_factory(workers=1) as (kind, executor, recorder):
        if kind != "process":
            pytest.skip("kill is only supported for tasks running in a subprocess")

        marker = tmp_path / "started"
        future = executor.submit_task(
            StartMarkerTask, inputs={"duration": 10, "marker": str(marker)}
        )
        _wait_without_events(marker.exists, timeout=60)
        time.sleep(0.5)  # let the relay queue "aboutToStart" and "started"

        assert future.kill()

        recorder.wait_for("finished", 1)
        recorder.assert_order(
            "submitted", "aboutToStart", "started", "killed", "failed", "finished"
        )


@pytest.mark.parametrize("concurrency", [Concurrency.THREAD, Concurrency.PROCESS])
def test_failed_submission_is_not_running(ewoksorange_qtapp, concurrency):
    """A submission that raises does not keep the executor busy."""
    pool = create_pool_executor(concurrency, max_workers=1)
    if concurrency is Concurrency.PROCESS:
        pool.close()
        pool.join()
    else:
        pool.shutdown()
    executor = EwoksExecutor(pool, SubmitPolicy.DROP_IF_BUSY)
    recorder = SignalRecorder()
    recorder.connect(executor)
    try:
        for _ in range(2):
            with pytest.raises(RuntimeError):
                executor.submit_task(AddTask, inputs={"a": 1})
        recorder.assert_counts()
    finally:
        executor.shutdown(wait=True)


def _wait_without_events(condition: Callable[[], bool], timeout: float = 10) -> None:
    """Wait for `condition` without processing the events of the GUI thread."""
    t0 = time.monotonic()
    while not condition():
        assert time.monotonic() - t0 < timeout, "timeout"
        time.sleep(0.01)
