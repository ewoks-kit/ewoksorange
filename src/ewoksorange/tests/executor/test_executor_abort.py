import os
import signal
import sys
import threading
import time

import pytest

from ...gui.concurrency.future import TaskAbortedError
from .tasks import CleanupTask
from .tasks import IgnoreStopTask
from .tasks import PidTask


def test_abort(ewoksorange_qtapp, executor_context_factory, tmp_path):
    """Abort interrupts a task running in a subprocess, even when it ignores stop
    requests. The task cleans up and the worker remains usable."""
    with executor_context_factory(workers=1) as (kind, executor, recorder):
        if kind != "process":
            pytest.skip("abort is only supported for tasks running in a subprocess")

        pid = (
            executor.submit_task(PidTask, inputs={"value": 1})
            .result(timeout=10)["pid"]
            .value
        )

        marker = tmp_path / "cleanup"
        executor.submit_task(
            CleanupTask, inputs={"duration": 10, "marker": str(marker)}
        )
        future = recorder.wait_future("started", index=1)

        t0 = time.monotonic()
        assert future.abort()

        with pytest.raises(TaskAbortedError, match="was aborted"):
            future.result(timeout=5)
        assert time.monotonic() - t0 < 5

        assert future.aborted()
        assert not future.killed()
        assert not future.stop_requested()
        assert not future.cancelled()
        assert marker.exists()

        recorder.wait_for("finished", 2)
        recorder.assert_counts(
            submitted=2,
            aboutToStart=2,
            started=2,
            succeeded=1,
            failed=1,
            aborted=1,
            finished=2,
        )

        outputs = executor.submit_task(PidTask, inputs={"value": 2}).result(timeout=10)
        assert outputs["value"].value == 2
        assert outputs["pid"].value == pid


def test_kill(ewoksorange_qtapp, executor_context_factory, tmp_path):
    """Kill terminates the subprocess running a task. The task does not clean up
    and the pool replaces the worker."""
    with executor_context_factory(workers=1) as (kind, executor, recorder):
        if kind != "process":
            pytest.skip("kill is only supported for tasks running in a subprocess")

        pid = (
            executor.submit_task(PidTask, inputs={"value": 1})
            .result(timeout=10)["pid"]
            .value
        )

        marker = tmp_path / "cleanup"
        executor.submit_task(
            CleanupTask, inputs={"duration": 10, "marker": str(marker)}
        )
        future = recorder.wait_future("started", index=1)

        t0 = time.monotonic()
        assert future.kill()

        with pytest.raises(TaskAbortedError, match="was killed"):
            future.result(timeout=5)
        assert time.monotonic() - t0 < 5
        assert isinstance(future.exception(), TaskAbortedError)

        assert future.killed()
        assert not future.aborted()
        assert not future.stop_requested()
        assert not future.cancelled()

        recorder.wait_for("finished", 2)
        recorder.assert_counts(
            submitted=2,
            aboutToStart=2,
            started=2,
            succeeded=1,
            failed=1,
            killed=1,
            finished=2,
        )

        outputs = executor.submit_task(PidTask, inputs={"value": 2}).result(timeout=10)
        assert outputs["value"].value == 2
        assert outputs["pid"].value != pid
        assert not marker.exists()


@pytest.mark.skipif(sys.platform == "win32", reason="requires POSIX signals")
def test_abort_signal_ignored_by_idle_worker(
    ewoksorange_qtapp, executor_context_factory
):
    """SIGINT does not kill an idle worker, which would break the pool."""
    with executor_context_factory(workers=1) as (kind, executor, recorder):
        if kind != "process":
            pytest.skip("abort is only supported for tasks running in a subprocess")

        pid = (
            executor.submit_task(PidTask, inputs={"value": 1})
            .result(timeout=10)["pid"]
            .value
        )

        os.kill(pid, signal.SIGINT)
        time.sleep(0.5)

        outputs = executor.submit_task(PidTask, inputs={"value": 2}).result(timeout=10)
        assert outputs["value"].value == 2
        assert outputs["pid"].value == pid


def test_abort_not_supported(ewoksorange_qtapp, executor_context_factory):
    """Abort and kill have no effect on a task that does not run in a subprocess."""
    with executor_context_factory() as (kind, executor, recorder):
        if kind == "process":
            pytest.skip("abort is supported for tasks running in a subprocess")

        inputs = {"duration": 0.3}
        thread = None
        if kind == "sync":
            thread = threading.Thread(
                target=executor.submit_task,
                args=(IgnoreStopTask,),
                kwargs={"inputs": inputs},
            )
            thread.start()
        else:
            executor.submit_task(IgnoreStopTask, inputs=inputs)

        future = recorder.wait_future("started")

        assert not future.abort()
        assert not future.kill()

        result = future.result(timeout=10)
        assert result["result"].value == "completed despite stop request"
        assert not future.aborted()
        assert not future.killed()

        recorder.wait_for("finished", 1)
        recorder.assert_counts(
            submitted=1, aboutToStart=1, started=1, succeeded=1, finished=1
        )
        if thread is not None:
            thread.join(timeout=10)
