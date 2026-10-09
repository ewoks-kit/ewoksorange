import os
import signal
import sys
import threading
import time

import pytest
from AnyQt.QtCore import Qt

from ...gui.concurrency.future import TaskAbortedError
from ...gui.concurrency.future import TaskKilledError
from ...gui.qt_utils.progress import QProgress
from .tasks import CleanupTask
from .tasks import IgnoreStopTask
from .tasks import PidTask
from .tasks import ProgressLoopTask
from .tasks import SlowInitTask
from .tasks import StartMarkerTask
from .tasks import SurviveAbortProgressTask
from .tasks import SurviveAbortTask
from .utils import assert_none_emitted


def test_abort(qtbot, executor_context_factory, tmp_path):
    """Abort interrupts a task running in a subprocess, even when it ignores stop
    requests. The task cleans up and the worker remains usable."""
    with executor_context_factory(workers=1) as (kind, executor):
        if kind != "process":
            pytest.skip("abort is only supported for tasks running in a subprocess")

        pid = _run_pid_task(qtbot, executor, 1)

        marker = tmp_path / "cleanup"
        with assert_none_emitted(
            qtbot,
            executor.succeeded,
            executor.cancelled,
            executor.stopRequested,
            executor.killed,
        ), qtbot.wait_signals(
            [executor.aborted, executor.failed, executor.finished],
            timeout=15_000,
            order="strict",
        ):
            with qtbot.wait_signal(executor.started, timeout=10_000) as signal_blocker:
                executor.submit_task(
                    CleanupTask, inputs={"duration": 10, "marker": str(marker)}
                )
            future = signal_blocker.args[0]

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

        assert _run_pid_task(qtbot, executor, 2) == pid


def test_abort_during_creation(qtbot, executor_context_factory):
    """Abort interrupts a task that is still being created when the abort arrives."""
    with executor_context_factory(workers=1) as (kind, executor):
        if kind != "process":
            pytest.skip("abort is only supported for tasks running in a subprocess")

        with qtbot.assert_not_emitted(executor.succeeded), qtbot.wait_signals(
            [executor.aborted, executor.failed, executor.finished],
            timeout=15_000,
            order="strict",
        ):
            with qtbot.wait_signal(
                executor.aboutToStart, timeout=10_000
            ) as signal_blocker:
                executor.submit_task(
                    SlowInitTask, inputs={"init_duration": 1, "duration": 10}
                )
            future = signal_blocker.args[0]

            assert future.abort()

            with pytest.raises(TaskAbortedError, match="was aborted"):
                future.result(timeout=5)

        assert future.aborted()


def test_abort_during_progress(qtbot, executor_context_factory, tmp_path):
    """Abort while the task reports progress leaves the worker usable: a task
    cancelled while queued for that worker never starts."""
    with executor_context_factory(workers=1) as (kind, executor):
        if kind != "process":
            pytest.skip("abort is only supported for tasks running in a subprocess")

        progress = QProgress()
        with qtbot.wait_signal(executor.finished, timeout=15_000):
            future = executor.submit_task(
                ProgressLoopTask, inputs={"duration": 30}, progress=progress
            )
            qtbot.wait_until(lambda: progress.progress > 0, timeout=10_000)
            assert future.abort()
            assert isinstance(future.exception(timeout=10), TaskAbortedError)

        marker = tmp_path / "queued"
        with qtbot.wait_signals([executor.finished] * 2, timeout=15_000):
            blocker = executor.submit_task(
                StartMarkerTask,
                inputs={"duration": 1, "marker": str(tmp_path / "blocker")},
            )
            queued = executor.submit_task(
                StartMarkerTask, inputs={"duration": 0, "marker": str(marker)}
            )
            assert queued.cancel()

            assert blocker.result(timeout=10)["result"].value == "completed"

        assert queued.cancelled()
        assert not marker.exists()


def test_abort_survived_keeps_progress(qtbot, executor_context_factory):
    """A task that survives an abort and completes keeps its progress."""
    with executor_context_factory(workers=1) as (kind, executor):
        if kind != "process":
            pytest.skip("abort is only supported for tasks running in a subprocess")

        progress = QProgress()
        with assert_none_emitted(
            qtbot, executor.failed, executor.aborted
        ), qtbot.wait_signals(
            [executor.succeeded, executor.finished], timeout=15_000, order="strict"
        ):
            with qtbot.wait_signal(executor.started, timeout=10_000) as signal_blocker:
                executor.submit_task(
                    SurviveAbortProgressTask, inputs={"timeout": 30}, progress=progress
                )
            future = signal_blocker.args[0]

            assert future.abort()

            assert future.result(timeout=10)["result"].value == "completed"
            assert not future.aborted()

        assert progress.progress == 100


def test_kill(qtbot, executor_context_factory, tmp_path):
    """Kill terminates the subprocess running a task. The task does not clean up
    and the pool replaces the worker."""
    with executor_context_factory(workers=1) as (kind, executor):
        if kind != "process":
            pytest.skip("kill is only supported for tasks running in a subprocess")

        pid = _run_pid_task(qtbot, executor, 1)

        marker = tmp_path / "cleanup"
        with assert_none_emitted(
            qtbot,
            executor.succeeded,
            executor.cancelled,
            executor.stopRequested,
            executor.aborted,
        ), qtbot.wait_signals(
            [executor.killed, executor.failed, executor.finished],
            timeout=15_000,
            order="strict",
        ):
            with qtbot.wait_signal(executor.started, timeout=10_000) as signal_blocker:
                executor.submit_task(
                    CleanupTask, inputs={"duration": 10, "marker": str(marker)}
                )
            future = signal_blocker.args[0]

            t0 = time.monotonic()
            assert future.kill()

            with pytest.raises(TaskKilledError, match="was killed"):
                future.result(timeout=5)
            assert time.monotonic() - t0 < 5
            assert isinstance(future.exception(), TaskKilledError)

        assert future.killed()
        assert not future.aborted()
        assert not future.stop_requested()
        assert not future.cancelled()

        assert _run_pid_task(qtbot, executor, 2) != pid
        assert not marker.exists()


def test_escalate(qtbot, executor_context_factory, tmp_path):
    """A running task that ignores a stop request and survives an abort is killed."""
    with executor_context_factory(workers=1) as (kind, executor):
        if kind != "process":
            pytest.skip("abort and kill are only supported in a subprocess")

        marker = tmp_path / "interrupted"
        with assert_none_emitted(
            qtbot, executor.succeeded, executor.aborted
        ), qtbot.wait_signals(
            [
                executor.stopRequested,
                executor.killed,
                executor.failed,
                executor.finished,
            ],
            timeout=15_000,
            order="strict",
        ):
            with qtbot.wait_signal(executor.started, timeout=10_000) as signal_blocker:
                executor.submit_task(
                    SurviveAbortTask, inputs={"duration": 30, "marker": str(marker)}
                )
            future = signal_blocker.args[0]

            assert future.request_stop()
            assert future.abort()
            t0 = time.monotonic()
            while not marker.exists():
                assert time.monotonic() - t0 < 5, "the abort did not reach the task"
                time.sleep(0.01)
            assert not future.done()

            assert future.kill()
            with pytest.raises(TaskKilledError, match="was killed"):
                future.result(timeout=5)

        assert future.stop_requested()
        assert not future.aborted()
        assert future.killed()


def test_kill_from_relay_thread(qtbot, executor_context_factory):
    """Kill from a slot that runs in the relay thread ends the execution."""
    with executor_context_factory(workers=1) as (kind, executor):
        if kind != "process":
            pytest.skip("kill is only supported for tasks running in a subprocess")

        executor.started.connect(
            lambda future: future.kill(), Qt.ConnectionType.DirectConnection
        )
        # The kill can overtake the delivery of `started` to the GUI thread:
        # the signals are not checked for their order.
        with assert_none_emitted(
            qtbot, executor.succeeded, executor.aborted
        ), qtbot.wait_signals(
            [
                executor.submitted,
                executor.aboutToStart,
                executor.started,
                executor.killed,
                executor.failed,
                executor.finished,
            ],
            timeout=15_000,
        ):
            future = executor.submit_task(IgnoreStopTask, inputs={"duration": 10})

            with pytest.raises(TaskKilledError, match="was killed"):
                future.result(timeout=5)


@pytest.mark.skipif(sys.platform == "win32", reason="requires POSIX signals")
def test_abort_signal_ignored_by_idle_worker(qtbot, executor_context_factory):
    """SIGINT does not kill an idle worker, which would break the pool."""
    with executor_context_factory(workers=1) as (kind, executor):
        if kind != "process":
            pytest.skip("abort is only supported for tasks running in a subprocess")

        pid = _run_pid_task(qtbot, executor, 1)

        os.kill(pid, signal.SIGINT)
        time.sleep(0.5)

        assert _run_pid_task(qtbot, executor, 2) == pid


def test_abort_not_supported(qtbot, executor_context_factory):
    """Abort and kill have no effect on a task that does not run in a subprocess."""
    with executor_context_factory() as (kind, executor):
        if kind == "process":
            pytest.skip("abort is supported for tasks running in a subprocess")

        inputs = {"duration": 0.3}
        thread = None
        with assert_none_emitted(
            qtbot, executor.failed, executor.aborted, executor.killed
        ), qtbot.wait_signals(
            [executor.succeeded, executor.finished], timeout=15_000, order="strict"
        ):
            with qtbot.wait_signal(executor.started, timeout=5_000) as signal_blocker:
                if kind == "sync":
                    thread = threading.Thread(
                        target=executor.submit_task,
                        args=(IgnoreStopTask,),
                        kwargs={"inputs": inputs},
                    )
                    thread.start()
                else:
                    executor.submit_task(IgnoreStopTask, inputs=inputs)
            future = signal_blocker.args[0]

            assert not future.abort()
            assert not future.kill()

            result = future.result(timeout=10)
            assert result["result"].value == "completed despite stop request"

        assert not future.aborted()
        assert not future.killed()

        if thread is not None:
            thread.join(timeout=10)


def _run_pid_task(qtbot, executor, value: int) -> int:
    """Run a `PidTask` to completion, including its signals, and return the
    process ID of the worker that executed it."""
    with qtbot.assert_not_emitted(executor.failed), qtbot.wait_signal(
        executor.finished, timeout=15_000
    ):
        outputs = executor.submit_task(PidTask, inputs={"value": value}).result(
            timeout=10
        )
    assert outputs["value"].value == value
    return outputs["pid"].value
