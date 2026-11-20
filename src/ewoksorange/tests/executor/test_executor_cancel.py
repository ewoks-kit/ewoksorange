import threading

import pytest

from ...gui.concurrency.executor import Concurrency
from .tasks import AddTask
from .tasks import IgnoreStopTask
from .utils import assert_signal_counts


def test_cancel_queued_task_sync(qtbot, executor_factory):
    """cancel() is no-op with synchronous executor."""
    executor = executor_factory(Concurrency.SYNC, workers=1)

    inputs = {"a": 1, "delay": 4}
    # submit_task() blocks until the task finishes, so it must run
    # on its own thread to still be "busy" when the rest are submitted.
    thread = threading.Thread(
        target=executor.submit_task, args=(AddTask,), kwargs={"inputs": inputs}
    )

    with assert_signal_counts(
        qtbot,
        executor,
        submitted=2,
        aboutToStart=2,
        started=2,
        succeeded=2,
        finished=2,
    ):
        with qtbot.wait_signal(executor.started) as signal_blocker:
            thread.start()

        blocker_future = signal_blocker.args[0]

        # Sync has no queue at all: submit_task() only returns once the task
        # has already run, so cancel() there is correctly a no-op because
        # already done, not merely unstarted.
        with qtbot.wait_signals(
            [
                executor.submitted,
                executor.started,
                executor.succeeded,
                executor.finished,
            ],
            order="strict",
            timeout=10_000,
        ):
            victim = executor.submit_task(AddTask, inputs={"a": 99})
            assert not victim.cancel()

        blocker_future.result(timeout=10)

    thread.join(timeout=10)


@pytest.mark.parametrize(
    "concurrency",
    [Concurrency.THREAD, Concurrency.PROCESS],
    ids=lambda c: c.name.lower(),
)
def test_cancel_queued_task(qtbot, concurrency, executor_factory):
    """cancel() prevents a genuinely queued task from ever running."""
    executor = executor_factory(concurrency, workers=1)

    # Only the blocker starts: the victim must never start.
    with assert_signal_counts(
        qtbot,
        executor,
        submitted=2,
        aboutToStart=1,
        started=1,
        succeeded=1,
        cancelled=1,
        finished=2,
    ):
        with qtbot.wait_signal(executor.started, timeout=10_000):
            blocker_future = executor.submit_task(AddTask, inputs={"a": 1, "delay": 2})

        victim = executor.submit_task(AddTask, inputs={"a": 99})
        assert victim.cancel() is True

        blocker_future.result(timeout=10)

    assert victim.cancelled()


def test_cancel_after_completion(qtbot, executor_context_factory):
    """cancel() on an already-finished task is a no-op."""
    with executor_context_factory() as (kind, executor):
        thread = None

        with qtbot.wait_signal(executor.succeeded) as signal_blocker:
            if kind == "sync":
                thread = threading.Thread(
                    target=executor.submit_task,
                    args=(AddTask,),
                    kwargs={"inputs": {"a": 1}},
                )
                thread.start()
            else:
                executor.submit_task(AddTask, inputs={"a": 1})

        future = signal_blocker.args[0]

        assert future.cancel() is False
        if thread is not None:
            thread.join(timeout=10)


def test_cancel_running_task(qtbot, executor_context_factory):
    """cancel() has no effect on a running task."""
    with executor_context_factory() as (kind, executor):
        inputs = {"duration": 0.3}
        thread = None

        with assert_signal_counts(
            qtbot,
            executor,
            submitted=1,
            aboutToStart=1,
            started=1,
            succeeded=1,
            finished=1,
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

            assert not future.cancel()

            result = future.result(timeout=10)
            assert result["result"].value == "completed despite stop request"
            assert not future.cancelled()

        if thread is not None:
            thread.join(timeout=10)
