import threading

import pytest
from ewoksutils.exceptions import TaskExecutionError

from ...gui.concurrency.executor import TaskFuture
from .tasks import AddTask
from .tasks import EarlyStopTask
from .tasks import IgnoreStopTask
from .tasks import InterruptStopTask
from .tasks import PartialStopTask
from .utils import assert_exception


def test_request_stop(qtbot, executor_context_factory):
    """Stop request observed by run(): it raises, so the task fails."""
    with executor_context_factory() as (kind, executor):
        inputs = {"a": 1, "b": 2, "delay": 5}
        thread = None

        with qtbot.assert_not_emitted(executor.succeeded), qtbot.wait_signals(
            (executor.aborted, executor.failed, executor.finished),
            check_params_cbs=[lambda future: future is submitted_future] * 3,
            timeout=15_000,
            order="strict",
        ):
            with qtbot.wait_signals(
                (executor.submitted, executor.aboutToStart, executor.started),
                check_params_cbs=[lambda future: isinstance(future, TaskFuture)] * 2,
                timeout=5_000,
                order="strict",
            ) as signals_blocker:
                if kind == "sync":
                    # submit_task() blocks until the task finishes, so it must run
                    # on its own thread for abort() to have anything to interrupt.
                    thread = threading.Thread(
                        target=executor.submit_task,
                        args=(AddTask,),
                        kwargs={"inputs": inputs},
                    )
                    thread.start()
                else:
                    executor.submit_task(AddTask, inputs=inputs)

            submitted_future = signals_blocker.all_signals_and_args[0].args[0]
            started_future = signals_blocker.all_signals_and_args[1].args[0]
            assert started_future is submitted_future

            assert submitted_future.request_stop()

            match = r"cancelled after [\.0-9]+ seconds"
            with pytest.raises(TaskExecutionError, match=match):
                submitted_future.result(timeout=10)

            assert submitted_future.stop_requested()

            assert_exception(
                submitted_future.exception(), TaskExecutionError, match=match
            )

        if thread is not None:
            thread.join(timeout=10)


@pytest.mark.parametrize("task_class", [EarlyStopTask, InterruptStopTask])
def test_stop_leaves_outputs_undefined(qtbot, executor_context_factory, task_class):
    """Stop request observed by run(): it returns early, so no output is set.

    Covers polling `Task.stop_requested` (EarlyStopTask) and reacting
    in `Task._on_stop_requested` (InterruptStopTask).
    """
    with executor_context_factory() as (kind, executor):
        inputs = {"duration": 2}
        thread = None

        with qtbot.assert_not_emitted(executor.failed), qtbot.wait_signals(
            (executor.aborted, executor.succeeded, executor.finished),
            check_params_cbs=[lambda future: future is submitted_future] * 3,
            timeout=15_000,
            order="strict",
        ):
            with qtbot.wait_signals(
                (executor.submitted, executor.aboutToStart, executor.started),
                check_params_cbs=[lambda future: isinstance(future, TaskFuture)] * 2,
                timeout=5_000,
                order="strict",
            ) as signals_blocker:
                if kind == "sync":
                    thread = threading.Thread(
                        target=executor.submit_task,
                        args=(task_class,),
                        kwargs={"inputs": inputs},
                    )
                    thread.start()
                else:
                    executor.submit_task(task_class, inputs=inputs)

            submitted_future = signals_blocker.all_signals_and_args[0].args[0]
            started_future = signals_blocker.all_signals_and_args[1].args[0]
            assert started_future is submitted_future

            assert submitted_future.request_stop()

            result = submitted_future.result(timeout=10)
            assert not result["result"].has_value

            assert submitted_future.stop_requested()

        if thread is not None:
            thread.join(timeout=10)


def test_stop_leaves_partial_outputs(qtbot, executor_context_factory):
    """Stop request observed by run(): it returns after only some outputs
    were set, leaving the rest undefined."""
    with executor_context_factory() as (kind, executor):
        inputs = {"duration": 2}
        thread = None

        with qtbot.assert_not_emitted(executor.failed), qtbot.wait_signals(
            (executor.aborted, executor.succeeded, executor.finished),
            check_params_cbs=[lambda future: future is submitted_future] * 3,
            timeout=15_000,
            order="strict",
        ):
            with qtbot.wait_signals(
                (executor.submitted, executor.aboutToStart, executor.started),
                check_params_cbs=[lambda future: isinstance(future, TaskFuture)] * 2,
                timeout=5_000,
                order="strict",
            ) as signals_blocker:
                if kind == "sync":
                    thread = threading.Thread(
                        target=executor.submit_task,
                        args=(PartialStopTask,),
                        kwargs={"inputs": inputs},
                    )
                    thread.start()
                else:
                    executor.submit_task(PartialStopTask, inputs=inputs)

            submitted_future = signals_blocker.all_signals_and_args[0].args[0]
            started_future = signals_blocker.all_signals_and_args[1].args[0]
            assert started_future is submitted_future

            assert submitted_future.request_stop()

            result = submitted_future.result(timeout=10)
            assert result["first"].value == "first done"
            assert not result["second"].has_value

            assert submitted_future.stop_requested()

        if thread is not None:
            thread.join(timeout=10)


def test_request_stop_does_not_guarantee_stop(qtbot, executor_context_factory):
    """A task that never checks `self.stop_requested` always completes normally.

    `stop_requested()` still reports True: it reflects that the stop request reached the task,
    not what the task chose to do about it.
    """
    with executor_context_factory() as (kind, executor):
        inputs = {"duration": 0.3}
        thread = None

        with qtbot.assert_not_emitted(executor.failed), qtbot.wait_signals(
            (executor.aborted, executor.succeeded, executor.finished),
            check_params_cbs=[lambda future: future is submitted_future] * 3,
            timeout=15_000,
            order="strict",
        ):
            with qtbot.wait_signals(
                (executor.submitted, executor.aboutToStart, executor.started),
                check_params_cbs=[lambda future: isinstance(future, TaskFuture)] * 2,
                timeout=5_000,
                order="strict",
            ) as signals_blocker:
                if kind == "sync":
                    thread = threading.Thread(
                        target=executor.submit_task,
                        args=(IgnoreStopTask,),
                        kwargs={"inputs": inputs},
                    )
                    thread.start()
                else:
                    executor.submit_task(IgnoreStopTask, inputs=inputs)

            submitted_future = signals_blocker.all_signals_and_args[0].args[0]
            started_future = signals_blocker.all_signals_and_args[1].args[0]
            assert started_future is submitted_future

            assert submitted_future.request_stop()

            result = submitted_future.result(timeout=10)
            assert result["result"].value == "completed despite abort"

            assert submitted_future.stop_requested()

        if thread is not None:
            thread.join(timeout=10)
