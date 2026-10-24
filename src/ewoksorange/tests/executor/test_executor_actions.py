from concurrent.futures import CancelledError
from typing import Dict

import pytest

from ...gui.concurrency._controllers.process import ProcessTaskController
from ...gui.concurrency.future import TaskAbortedError
from ...gui.concurrency.future import TaskFuture
from ...gui.concurrency.future import TaskKilledError
from ...gui.concurrency.future import TaskStoppedError
from .tasks import AddTask

_ACTIONS = ("cancel", "request_stop", "abort", "kill")

_SUBPROCESS_ONLY = ("abort", "kill")

_ERRORS = {
    "cancel": (CancelledError, None),
    "request_stop": (TaskStoppedError, "stopped before it started"),
    "abort": (TaskAbortedError, "aborted before it started"),
    "kill": (TaskKilledError, "killed before it started"),
}

_SIGNALS = {
    "cancel": {"cancelled": 1, "finished": 1},
    "request_stop": {"stopRequested": 1, "failed": 1, "finished": 1},
    "abort": {"aborted": 1, "failed": 1, "finished": 1},
    "kill": {"killed": 1, "failed": 1, "finished": 1},
}


@pytest.mark.parametrize("action", _ACTIONS)
def test_queued_task_never_starts(ewoksorange_qtapp, executor_context_factory, action):
    """Each action prevents a queued task from starting, with its own outcome."""
    with executor_context_factory(workers=1) as (kind, executor, recorder):
        if kind == "sync":
            pytest.skip("sync execution has no queue")

        blocker = executor.submit_task(AddTask, inputs={"a": 1, "delay": 1})
        recorder.wait_for("started")
        queued = executor.submit_task(AddTask, inputs={"a": 2})

        supported = kind == "process" or action not in _SUBPROCESS_ONLY
        assert getattr(queued, action)() is supported

        assert blocker.result(timeout=10)["result"].value == 1

        if not supported:
            assert queued.result(timeout=10)["result"].value == 2
            assert _flags(queued) == dict.fromkeys(_ACTIONS, False)
            recorder.wait_for("finished", 2)
            recorder.assert_counts(
                submitted=2, aboutToStart=2, started=2, succeeded=2, finished=2
            )
            return

        exc_type, match = _ERRORS[action]
        with pytest.raises(exc_type, match=match):
            queued.result(timeout=10)
        assert _flags(queued) == {name: name == action for name in _ACTIONS}

        expected = {
            "submitted": 2,
            "aboutToStart": 1,
            "started": 1,
            "succeeded": 1,
            "finished": 1,
        }
        for name, count in _SIGNALS[action].items():
            expected[name] = expected.get(name, 0) + count
        recorder.wait_for("finished", expected["finished"])
        recorder.assert_counts(**expected)
        recorder.assert_started(blocker)
        assert queued not in recorder.futures("aboutToStart")
        assert queued not in recorder.futures("started")


@pytest.mark.parametrize("first", _ACTIONS)
def test_queued_task_first_action_wins(
    ewoksorange_qtapp, executor_context_factory, first
):
    """Only the first action that reaches a queued task has an effect."""
    with executor_context_factory(workers=1) as (kind, executor, recorder):
        if kind != "process":
            pytest.skip("abort and kill are only supported in a subprocess")

        blocker = executor.submit_task(AddTask, inputs={"a": 1, "delay": 1})
        recorder.wait_for("started")
        queued = executor.submit_task(AddTask, inputs={"a": 2})

        assert getattr(queued, first)()
        for action in _ACTIONS:
            assert not getattr(queued, action)(), action

        blocker.result(timeout=10)
        exc_type, match = _ERRORS[first]
        with pytest.raises(exc_type, match=match):
            queued.result(timeout=10)
        assert _flags(queued) == {name: name == first for name in _ACTIONS}


def test_killed_queued_task_completes(ewoksorange_qtapp, executor_context_factory):
    """Kill completes the future of a queued task right away."""
    with executor_context_factory(workers=1) as (kind, executor, recorder):
        if kind != "process":
            pytest.skip("kill is only supported in a subprocess")

        blocker = executor.submit_task(AddTask, inputs={"a": 1, "delay": 2})
        recorder.wait_for("started")
        queued = executor.submit_task(AddTask, inputs={"a": 2})

        assert queued.kill()
        assert queued.done()
        assert not blocker.done()
        with pytest.raises(TaskKilledError, match="killed before it started"):
            queued.result(timeout=0)

        recorder.wait_for("finished", 1)
        assert recorder.future("finished") is queued
        assert blocker.result(timeout=10)["result"].value == 1


def test_failed_watch_ends_execution(
    ewoksorange_qtapp, executor_context_factory, monkeypatch
):
    """When the relay fails to start, the submission raises, the execution ends
    with `cancelled` and `finished`, and the executor stays usable."""
    with executor_context_factory(workers=1) as (kind, executor, recorder):
        if kind != "process":
            pytest.skip("only the process backend watches the task")

        def _failing_watch(*args, **kwargs) -> None:
            raise RuntimeError("cannot start the relay")

        # Last resort: starting a thread cannot be made to fail otherwise.
        with monkeypatch.context() as patch:
            patch.setattr(ProcessTaskController, "watch", _failing_watch)
            with pytest.raises(RuntimeError, match="cannot start the relay"):
                executor.submit_task(AddTask, inputs={"a": 1})

        recorder.assert_counts(submitted=1, cancelled=1, finished=1)
        assert recorder.future("finished").cancelled()

        future = executor.submit_task(AddTask, inputs={"a": 2})
        assert future.result(timeout=30)["result"].value == 2


def test_finished_task(ewoksorange_qtapp, executor_context_factory):
    """No action has an effect on a finished task."""
    with executor_context_factory() as (kind, executor, recorder):
        future = executor.submit_task(AddTask, inputs={"a": 1})
        assert future.result(timeout=10)["result"].value == 1

        for action in _ACTIONS:
            assert not getattr(future, action)(), action

        assert future.result()["result"].value == 1
        assert _flags(future) == dict.fromkeys(_ACTIONS, False)

        recorder.wait_for("finished", 1)
        recorder.assert_counts(
            submitted=1, aboutToStart=1, started=1, succeeded=1, finished=1
        )


def _flags(future: TaskFuture) -> Dict[str, bool]:
    """Which action had an effect, according to the future."""
    return {
        "cancel": future.cancelled(),
        "request_stop": future.stop_requested(),
        "abort": future.aborted(),
        "kill": future.killed(),
    }
