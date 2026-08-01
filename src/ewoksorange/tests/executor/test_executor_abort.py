import threading

import pytest
from ewoksutils.exceptions import TaskExecutionError

from .tasks import AddTask
from .tasks import IgnoreCancelTask
from .tasks import PartialCancelTask
from .tasks import RequestCancelTask
from .tasks import StateCancelTask


def test_abort(qtapp, executor_context_factory):
    """Cancellation observed by run(): it raises, so the task fails."""
    with executor_context_factory() as (kind, executor, recorder):
        inputs = {"a": 1, "b": 2, "delay": 5}
        thread = None
        if kind == "sync":
            # submit_task() blocks until the task finishes, so it must run
            # on its own thread for abort() to have anything to interrupt.
            thread = threading.Thread(
                target=executor.submit_task, args=(AddTask,), kwargs={"inputs": inputs}
            )
            thread.start()
        else:
            executor.submit_task(AddTask, inputs=inputs)

        future = recorder.wait_future("started")

        assert future.abort()

        match = r"cancelled after [\.0-9]+ seconds"
        with pytest.raises(TaskExecutionError, match=match):
            future.result(timeout=10)

        assert future.aborted()

        recorder.wait_for("finished", 1)
        recorder.assert_counts(submitted=1, started=1, aborted=1, failed=1, finished=1)
        recorder.assert_failed(future, TaskExecutionError, match=match)
        if thread is not None:
            thread.join(timeout=10)


@pytest.mark.parametrize("task_class", [RequestCancelTask, StateCancelTask])
def test_abort_leaves_outputs_undefined(qtapp, executor_context_factory, task_class):
    """Cancellation observed by run(): it returns early, so no output is set.

    Covers both interpretations of `Task.cancelled` (RequestCancelTask:
    request, StateCancelTask: state).
    """
    with executor_context_factory() as (kind, executor, recorder):
        inputs = {"duration": 2}
        thread = None
        if kind == "sync":
            thread = threading.Thread(
                target=executor.submit_task,
                args=(task_class,),
                kwargs={"inputs": inputs},
            )
            thread.start()
        else:
            executor.submit_task(task_class, inputs=inputs)

        future = recorder.wait_future("started")

        assert future.abort()

        result = future.result(timeout=10)
        assert not result["result"].has_value

        assert future.aborted()

        recorder.wait_for("finished", 1)
        recorder.assert_counts(
            submitted=1, started=1, succeeded=1, finished=1, aborted=1
        )
        if thread is not None:
            thread.join(timeout=10)


def test_abort_leaves_partial_outputs(qtapp, executor_context_factory):
    """Cancellation observed by run(): it returns after only some outputs
    were set, leaving the rest undefined."""
    with executor_context_factory() as (kind, executor, recorder):
        inputs = {"duration": 2}
        thread = None
        if kind == "sync":
            thread = threading.Thread(
                target=executor.submit_task,
                args=(PartialCancelTask,),
                kwargs={"inputs": inputs},
            )
            thread.start()
        else:
            executor.submit_task(PartialCancelTask, inputs=inputs)

        future = recorder.wait_future("started")

        assert future.abort()

        result = future.result(timeout=10)
        assert result["first"].value == "first done"
        assert not result["second"].has_value

        assert future.aborted()

        recorder.wait_for("finished", 1)
        recorder.assert_counts(
            submitted=1, started=1, succeeded=1, finished=1, aborted=1
        )
        if thread is not None:
            thread.join(timeout=10)


def test_abort_does_not_guarantee_cancellation(qtapp, executor_context_factory):
    """A task that never checks `self.cancelled` always completes normally.

    `aborted()` still reports True: it reflects that abort reached the task,
    not what the task chose to do about it.
    """
    with executor_context_factory() as (kind, executor, recorder):
        inputs = {"duration": 0.3}
        thread = None
        if kind == "sync":
            thread = threading.Thread(
                target=executor.submit_task,
                args=(IgnoreCancelTask,),
                kwargs={"inputs": inputs},
            )
            thread.start()
        else:
            executor.submit_task(IgnoreCancelTask, inputs=inputs)

        future = recorder.wait_future("started")

        assert future.abort()

        result = future.result(timeout=10)
        assert result["result"].value == "completed despite abort"

        assert future.aborted()

        recorder.wait_for("finished", 1)
        recorder.assert_counts(
            submitted=1, started=1, succeeded=1, finished=1, aborted=1
        )
        if thread is not None:
            thread.join(timeout=10)
