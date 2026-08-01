import threading

from ...gui.concurrency.executor import SubmitPolicy
from .tasks import AddTask


def test_drop_if_busy(qtapp, executor_context_factory):
    with executor_context_factory(SubmitPolicy.DROP_IF_BUSY, workers=1) as (
        kind,
        executor,
        recorder,
    ):
        inputs = {"a": 1, "delay": 2}
        thread = None
        if kind == "sync":
            # submit_task() blocks until the task finishes, so it must run
            # on its own thread to still be "busy" when the second is submitted.
            thread = threading.Thread(
                target=executor.submit_task, args=(AddTask,), kwargs={"inputs": inputs}
            )
            thread.start()
        else:
            executor.submit_task(AddTask, inputs=inputs)

        first = recorder.wait_future("started")

        # Every submission while busy is dropped, not just the first excess one.
        extra = [executor.submit_task(AddTask, inputs={"a": i}) for i in range(4)]
        assert extra == [None] * len(extra)

        first.result(timeout=10)

        recorder.wait_for("finished", 1)
        recorder.assert_counts(
            submitted=1, ignored=len(extra), started=1, succeeded=1, finished=1
        )
        if thread is not None:
            thread.join(timeout=10)


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
