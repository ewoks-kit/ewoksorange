import threading

from ...gui.concurrency.executor import SubmitPolicy
from .tasks import AddTask


def test_cancel_queued_task(qtapp, executor_context_factory):
    """cancel() prevents a genuinely queued task from ever running."""
    with executor_context_factory(SubmitPolicy.ALWAYS, workers=1) as (
        kind,
        executor,
        recorder,
    ):
        inputs = {"a": 1, "delay": 2}
        thread = None
        if kind == "sync":
            # submit_task() blocks until the task finishes, so it must run
            # on its own thread to still be "busy" when the rest are submitted.
            thread = threading.Thread(
                target=executor.submit_task, args=(AddTask,), kwargs={"inputs": inputs}
            )
            thread.start()
        else:
            executor.submit_task(AddTask, inputs=inputs)

        blocker = recorder.wait_future("started")

        # ProcessPoolExecutor feeds its worker's call queue ahead of time
        # (EXTRA_QUEUED_CALLS), so with a single worker the first couple of
        # queued submissions can already be uncancellable before they truly
        # start. A few filler submissions guarantee the last one is still
        # genuinely queued when it gets cancelled below.
        fillers = [executor.submit_task(AddTask, inputs={"a": i}) for i in range(4)]

        victim = executor.submit_task(AddTask, inputs={"a": 99})
        cancelled = victim.cancel()

        if kind == "sync":
            # Sync has no queue at all: submit_task() only returns once the task has
            # already run, so cancel() there is correctly a no-op because already done,
            # not merely unstarted.

            assert cancelled is False
            n_ran = 1 + len(fillers) + 1
        else:
            assert cancelled is True
            n_ran = 1 + len(fillers)

        blocker.result(timeout=10)
        for filler in fillers:
            filler.result(timeout=10)

        recorder.wait_for("finished", n_ran)
        recorder.assert_counts(
            submitted=1 + len(fillers) + 1,
            started=n_ran,
            succeeded=n_ran,
            finished=n_ran,
        )
        if thread is not None:
            thread.join(timeout=10)


def test_cancel_after_completion(qtapp, executor_context_factory):
    """cancel() on an already-finished task is a no-op."""
    with executor_context_factory() as (kind, executor, recorder):
        thread = None
        if kind == "sync":
            thread = threading.Thread(
                target=executor.submit_task,
                args=(AddTask,),
                kwargs={"inputs": {"a": 1}},
            )
            thread.start()
        else:
            executor.submit_task(AddTask, inputs={"a": 1})

        future = recorder.wait_future("succeeded")

        assert future.cancel() is False
        if thread is not None:
            thread.join(timeout=10)
