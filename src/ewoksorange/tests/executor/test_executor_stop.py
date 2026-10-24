import threading

import pytest
from ewoksutils.exceptions import TaskExecutionError

from .tasks import AddTask
from .tasks import EarlyStopTask
from .tasks import InterruptStopTask
from .tasks import PartialStopTask
from .tasks import WaitForFileTask


def test_request_stop(ewoksorange_qtapp, executor_context_factory):
    """Stop request observed by run(): it raises, so the task fails."""
    with executor_context_factory() as (kind, executor, recorder):
        inputs = {"a": 1, "b": 2, "delay": 5}
        thread = None
        if kind == "sync":
            # submit_task() blocks until the task finishes, so it must run
            # on its own thread for request_stop() to have anything to interrupt.
            thread = threading.Thread(
                target=executor.submit_task, args=(AddTask,), kwargs={"inputs": inputs}
            )
            thread.start()
        else:
            executor.submit_task(AddTask, inputs=inputs)

        future = recorder.wait_future("started")

        assert future.request_stop()

        match = r"stopped after [\.0-9]+ seconds"
        with pytest.raises(TaskExecutionError, match=match):
            future.result(timeout=10)

        assert future.stop_requested()

        recorder.wait_for("finished", 1)
        recorder.assert_counts(
            submitted=1,
            aboutToStart=1,
            started=1,
            stop_requested=1,
            failed=1,
            finished=1,
        )
        recorder.assert_failed(future, TaskExecutionError, match=match)
        if thread is not None:
            thread.join(timeout=10)


@pytest.mark.parametrize("task_class", [EarlyStopTask, InterruptStopTask])
def test_stop_leaves_outputs_undefined(
    ewoksorange_qtapp, executor_context_factory, task_class
):
    """Stop request observed by run(): it returns early, so no output is set.

    Covers polling `Task.stop_requested` (EarlyStopTask) and reacting
    in `Task._on_stop_requested` (InterruptStopTask).
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

        assert future.request_stop()

        result = future.result(timeout=10)
        assert not result["result"].has_value

        assert future.stop_requested()

        recorder.wait_for("finished", 1)
        recorder.assert_counts(
            submitted=1,
            aboutToStart=1,
            started=1,
            succeeded=1,
            finished=1,
            stop_requested=1,
        )
        if thread is not None:
            thread.join(timeout=10)


def test_stop_leaves_partial_outputs(ewoksorange_qtapp, executor_context_factory):
    """Stop request observed by run(): it returns after only some outputs
    were set, leaving the rest undefined."""
    with executor_context_factory() as (kind, executor, recorder):
        inputs = {"duration": 2}
        thread = None
        if kind == "sync":
            thread = threading.Thread(
                target=executor.submit_task,
                args=(PartialStopTask,),
                kwargs={"inputs": inputs},
            )
            thread.start()
        else:
            executor.submit_task(PartialStopTask, inputs=inputs)

        future = recorder.wait_future("started")

        assert future.request_stop()

        result = future.result(timeout=10)
        assert result["first"].value == "first done"
        assert not result["second"].has_value

        assert future.stop_requested()

        recorder.wait_for("finished", 1)
        recorder.assert_counts(
            submitted=1,
            aboutToStart=1,
            started=1,
            succeeded=1,
            finished=1,
            stop_requested=1,
        )
        if thread is not None:
            thread.join(timeout=10)


def test_request_stop_does_not_guarantee_stop(
    ewoksorange_qtapp, executor_context_factory, tmp_path
):
    """A task that never checks `self.stop_requested` always completes normally.

    `stop_requested()` still reports True: it reflects that the stop request reached the task,
    not what the task chose to do about it.
    """
    with executor_context_factory() as (kind, executor, recorder):
        release = tmp_path / "release"
        inputs = {"path": str(release)}
        thread = None
        if kind == "sync":
            thread = threading.Thread(
                target=executor.submit_task,
                args=(WaitForFileTask,),
                kwargs={"inputs": inputs},
            )
            thread.start()
        else:
            executor.submit_task(WaitForFileTask, inputs=inputs)

        future = recorder.wait_future("started")

        assert future.request_stop()
        release.touch()

        result = future.result(timeout=10)
        assert result["result"].value == "completed despite stop request"

        assert future.stop_requested()

        recorder.wait_for("finished", 1)
        recorder.assert_counts(
            submitted=1,
            aboutToStart=1,
            started=1,
            succeeded=1,
            finished=1,
            stop_requested=1,
        )
        if thread is not None:
            thread.join(timeout=10)
