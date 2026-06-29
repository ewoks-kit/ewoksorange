"""Tests for EwoksExecutor."""

import time
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor

import pytest
from ewokscore import Task
from ewokscore.missing_data import MissingData
from ewokscore.tests.examples.tasks.sumtask import SumTask as _SumTask

from ewoksorange.gui.concurrency.executor.EwoksExecutor import EwoksExecutor
from ewoksorange.gui.concurrency.executor.EwoksExecutor import SubmitPolicy
from ewoksorange.gui.qt_utils.app import QtEvent


class SumTask(_SumTask):
    def cancel(self):
        pass


class FailTask(Task, input_names=[], output_names=[]):
    def run(self):
        raise RuntimeError("deliberate failure")

    def cancel(self):
        pass


class SleepTask(Task, input_names=("duration",), output_names=("result",)):
    """Long-running task; abort() will cut it short by setting _cancelled."""

    def run(self):
        step = 0.05
        elapsed = 0.0
        while elapsed < self.inputs.duration:
            if self.cancelled:
                return
            time.sleep(step)
            elapsed += step
        self.outputs.result = f"slept {elapsed:.2f}s"

    def cancel(self):
        self._cancelled = True


def _output_values(output_variables) -> dict:
    return {k: v.value for k, v in output_variables.items()}


def _make_executor(policy=SubmitPolicy.ALWAYS, workers=1):
    return EwoksExecutor(ThreadPoolExecutor(max_workers=workers), policy)


@pytest.fixture(
    params=[
        pytest.param(
            (ThreadPoolExecutor, 1, SubmitPolicy.DROP_IF_BUSY), id="thread-1-drop"
        ),
        pytest.param((ThreadPoolExecutor, 1, SubmitPolicy.ALWAYS), id="thread-1-queue"),
        pytest.param(
            (ThreadPoolExecutor, 4, SubmitPolicy.ALWAYS), id="thread-4-parallel"
        ),
        pytest.param(
            (ProcessPoolExecutor, 2, SubmitPolicy.ALWAYS), id="process-2-parallel"
        ),
    ]
)
def executor(request, qtapp):
    PoolClass, workers, policy = request.param
    exe = EwoksExecutor(PoolClass(max_workers=workers), policy)
    yield exe
    exe.shutdown(wait=False)


def test_submit_task_succeeded(executor):
    result_holder = {}
    done = QtEvent()

    executor.succeeded.connect(
        lambda task_future, result: (
            result_holder.update({"result": result}),
            done.set(),
        )
    )

    task_future = executor.submit_task(SumTask, inputs={"a": 3, "b": 4})
    assert task_future is not None
    assert done.wait(timeout=5)
    assert _output_values(result_holder["result"]) == {"result": 7}


def test_submit_task_failed(executor):
    exc_holder = {}
    done = QtEvent()

    executor.failed.connect(
        lambda task_future, exception: (
            exc_holder.update({"exception": exception}),
            done.set(),
        )
    )

    task_future = executor.submit_task(FailTask)
    assert task_future is not None
    assert done.wait(timeout=5)
    assert isinstance(exc_holder["exception"], RuntimeError)
    assert "deliberate failure" in str(exc_holder["exception"])


def test_abort_running_task(executor):
    """abort() exits the task early; succeeded fires with MISSING_DATA output."""
    started = QtEvent()
    done = QtEvent()
    result_holder = {}

    executor.started.connect(lambda task_future: started.set())
    executor.succeeded.connect(
        lambda task_future, result: (
            result_holder.update({"result": result}),
            done.set(),
        )
    )
    executor.failed.connect(
        lambda task_future, exception: (
            result_holder.update({"exception": exception}),
            done.set(),
        )
    )

    task_future = executor.submit_task(SleepTask, inputs={"duration": 60.0})
    assert started.wait(timeout=5), "task never started"

    task_future.abort()

    assert done.wait(timeout=5)
    assert "result" in result_holder, f"expected succeeded, got: {result_holder}"
    assert isinstance(_output_values(result_holder["result"])["result"], MissingData)


def test_submitted_returns_task_future(executor):
    done = QtEvent()

    executor.succeeded.connect(lambda task_future, result: done.set())

    task_future = executor.submit_task(SumTask, inputs={"a": 1, "b": 1})
    assert task_future is not None
    assert done.wait(timeout=5)


def test_drop_if_busy_policy(qtapp):
    """DROP_IF_BUSY silently ignores submissions while the executor is busy."""
    submitted_count = [0]
    ignored_count = [0]
    done = QtEvent()

    exe = _make_executor(policy=SubmitPolicy.DROP_IF_BUSY, workers=1)
    exe.submitted.connect(
        lambda task_future: submitted_count.__setitem__(0, submitted_count[0] + 1)
    )
    exe.ignored.connect(lambda: ignored_count.__setitem__(0, ignored_count[0] + 1))
    exe.succeeded.connect(lambda task_future, result: done.set())

    # First submit starts, the rest should be dropped
    for _ in range(5):
        exe.submit_task(SleepTask, inputs={"duration": 0.3})

    assert done.wait(timeout=10)
    assert submitted_count[0] == 1
    assert ignored_count[0] == 4
    exe.shutdown()


def test_cancel_queued_task(qtapp):
    """cancel() on a pending future returns True and prevents execution.

    Requires ALWAYS policy with a single worker so the second task queues
    behind the first rather than starting immediately or being dropped.
    """
    done = QtEvent()
    second_ran = [False]

    exe = _make_executor(policy=SubmitPolicy.ALWAYS, workers=1)
    exe.succeeded.connect(lambda task_future, result: done.set())

    # Block the single worker thread
    exe.submit_task(SleepTask, inputs={"duration": 2.0})
    time.sleep(0.1)  # ensure the blocker has started

    # This one is pending — cancel it before it runs
    tf = exe.submit_task(SumTask, inputs={"a": 1, "b": 2})
    exe.succeeded.connect(lambda task_future, result: second_ran.__setitem__(0, True))
    cancelled = tf.cancel()

    assert cancelled is True
    assert not second_ran[0]
    exe.shutdown(wait=False)


def test_multiple_parallel_tasks(qtapp):
    """Four tasks complete concurrently when given four worker threads."""
    results = []
    done = QtEvent()

    exe = _make_executor(policy=SubmitPolicy.ALWAYS, workers=4)
    exe.succeeded.connect(
        lambda task_future, result: (
            results.append(_output_values(result)["result"]),
            (done.set() if len(results) == 4 else None),
        )
    )

    for i in range(4):
        exe.submit_task(SumTask, inputs={"a": i, "b": i})

    assert done.wait(timeout=10)
    assert sorted(results) == [0, 2, 4, 6]
    exe.shutdown()
