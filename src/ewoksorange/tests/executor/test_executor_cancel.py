import threading

import pytest

from ...gui.concurrency.executor import Concurrency
from .tasks import AddTask


def test_cancel_queued_task_sync(qtbot, executor_factory):
    """cancel() is no-op with synchronous executor."""
    executor = executor_factory(Concurrency.SYNC, workers=1)

    inputs = {"a": 1, "delay": 4}
    thread = None
    # submit_task() blocks until the task finishes, so it must run
    # on its own thread to still be "busy" when the rest are submitted.
    thread = threading.Thread(
        target=executor.submit_task, args=(AddTask,), kwargs={"inputs": inputs}
    )
    with qtbot.wait_signal(executor.started) as signal_blocker:
        thread.start()

    blocker_future = signal_blocker.args[0]

    # Sync has no queue at all: submit_task() only returns once the task has
    # already run, so cancel() there is correctly a no-op because already done,
    # not merely unstarted.
    with qtbot.wait_signals(
        [executor.submitted, executor.started, executor.succeeded, executor.finished],
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

    with qtbot.wait_signals([executor.submitted, executor.started], timeout=1_000):
        blocker_future = executor.submit_task(AddTask, inputs={"a": 1, "delay": 4})

    with qtbot.wait_signals([executor.submitted] * 5, timeout=2_000):
        # ProcessPoolExecutor feeds its worker's call queue ahead of time
        # (EXTRA_QUEUED_CALLS), so with a single worker the first couple of
        # queued submissions can already be uncancellable before they truly
        # start. A few filler submissions guarantee the last one is still
        # genuinely queued when it gets cancelled below.
        fillers = [executor.submit_task(AddTask, inputs={"a": i}) for i in range(4)]

        victim = executor.submit_task(AddTask, inputs={"a": 99})
        cancelled = victim.cancel()
        assert cancelled is True

    with qtbot.wait_signals(
        [executor.succeeded, executor.finished]
        + [executor.started, executor.succeeded, executor.finished] * 4,
        timeout=10_000,
    ):
        blocker_future.result(timeout=10)
        for filler in fillers:
            filler.result(timeout=10)


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
