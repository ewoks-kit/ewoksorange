import threading

from ...gui.concurrency.executor import SubmitPolicy
from .tasks import AddTask
from .tasks import IgnoreStopTask


def test_cancel_queued_task(ewoksorange_qtapp, executor_context_factory):
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

        victim = executor.submit_task(AddTask, inputs={"a": 99})
        cancelled = victim.cancel()

        if kind == "sync":
            # Sync has no queue at all: submit_task() only returns once the task has
            # already run, so cancel() there is correctly a no-op because already done,
            # not merely unstarted.

            assert cancelled is False
            n_ran = 2
        else:
            assert cancelled is True
            n_ran = 1
        n_cancelled = 2 - n_ran

        blocker.result(timeout=10)

        recorder.wait_for("finished", n_ran + n_cancelled)
        recorder.assert_counts(
            submitted=2,
            aboutToStart=n_ran,
            started=n_ran,
            succeeded=n_ran,
            cancelled=n_cancelled,
            finished=n_ran + n_cancelled,
        )
        if thread is not None:
            thread.join(timeout=10)


def test_cancel_after_completion(ewoksorange_qtapp, executor_context_factory):
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


def test_cancel_running_task(ewoksorange_qtapp, executor_context_factory):
    """cancel() has no effect on a running task."""
    with executor_context_factory() as (kind, executor, recorder):
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

        assert not future.cancel()

        result = future.result(timeout=10)
        assert result["result"].value == "completed despite stop request"
        assert not future.cancelled()

        recorder.wait_for("finished", 1)
        recorder.assert_counts(
            submitted=1, aboutToStart=1, started=1, succeeded=1, finished=1
        )
        if thread is not None:
            thread.join(timeout=10)
