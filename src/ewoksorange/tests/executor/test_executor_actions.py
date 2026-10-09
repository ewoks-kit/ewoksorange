from concurrent.futures import CancelledError
from typing import Dict

import pytest

from ...gui.concurrency._controllers.process import ProcessTaskController
from ...gui.concurrency.future import TaskAbortedError
from ...gui.concurrency.future import TaskFuture
from ...gui.concurrency.future import TaskKilledError
from ...gui.concurrency.future import TaskStoppedError
from .tasks import AddTask
from .utils import assert_none_emitted

_ACTIONS = ("cancel", "request_stop", "abort", "kill")

_SUBPROCESS_ONLY = ("abort", "kill")

_ERRORS = {
    "cancel": (CancelledError, None),
    "request_stop": (TaskStoppedError, "stopped before it started"),
    "abort": (TaskAbortedError, "aborted before it started"),
    "kill": (TaskKilledError, "killed before it started"),
}

# The signals emitted for a queued task, besides `submitted`.
_SIGNALS = {
    "cancel": ("cancelled", "finished"),
    "request_stop": ("stopRequested", "failed", "finished"),
    "abort": ("aborted", "failed", "finished"),
    "kill": ("killed", "failed", "finished"),
}

_OUTCOME_SIGNALS = (
    "succeeded",
    "failed",
    "cancelled",
    "stopRequested",
    "aborted",
    "killed",
)


@pytest.mark.parametrize("action", _ACTIONS)
def test_queued_task_never_starts(qtbot, executor_context_factory, action):
    """Each action prevents a queued task from starting, with its own outcome."""
    with executor_context_factory(workers=1) as (kind, executor):
        if kind == "sync":
            pytest.skip("sync execution has no queue")

        with qtbot.wait_signal(executor.started, timeout=10_000) as signal_blocker:
            blocker = executor.submit_task(AddTask, inputs={"a": 1, "delay": 1})
        assert signal_blocker.args[0] is blocker

        supported = kind == "process" or action not in _SUBPROCESS_ONLY

        if not supported:
            expected = ["submitted", "aboutToStart", "started"] + [
                "succeeded",
                "finished",
            ] * 2
            not_emitted = [name for name in _OUTCOME_SIGNALS if name != "succeeded"]
        else:
            # `aboutToStart` and `started` of the blocker were already received:
            # the queued task must never start.
            expected = ["submitted", "succeeded", "finished", *_SIGNALS[action]]
            not_emitted = ["aboutToStart", "started"] + [
                name
                for name in _OUTCOME_SIGNALS
                if name != "succeeded" and name not in _SIGNALS[action]
            ]

        with assert_none_emitted(
            qtbot, *(getattr(executor, name) for name in not_emitted)
        ), qtbot.wait_signals(
            [getattr(executor, name) for name in expected], timeout=20_000
        ):
            queued = executor.submit_task(AddTask, inputs={"a": 2})
            assert getattr(queued, action)() is supported

            assert blocker.result(timeout=10)["result"].value == 1

            if supported:
                exc_type, match = _ERRORS[action]
                with pytest.raises(exc_type, match=match):
                    queued.result(timeout=10)
            else:
                assert queued.result(timeout=10)["result"].value == 2

        if supported:
            assert _flags(queued) == {name: name == action for name in _ACTIONS}
        else:
            assert _flags(queued) == dict.fromkeys(_ACTIONS, False)


@pytest.mark.parametrize("first", _ACTIONS)
def test_queued_task_first_action_wins(qtbot, executor_context_factory, first):
    """Only the first action that reaches a queued task has an effect."""
    with executor_context_factory(workers=1) as (kind, executor):
        if kind != "process":
            pytest.skip("abort and kill are only supported in a subprocess")

        with qtbot.wait_signal(executor.started, timeout=10_000):
            blocker = executor.submit_task(AddTask, inputs={"a": 1, "delay": 1})

        with qtbot.wait_signals([executor.finished] * 2, timeout=20_000):
            queued = executor.submit_task(AddTask, inputs={"a": 2})

            assert getattr(queued, first)()
            for action in _ACTIONS:
                assert not getattr(queued, action)(), action

            blocker.result(timeout=10)
            exc_type, match = _ERRORS[first]
            with pytest.raises(exc_type, match=match):
                queued.result(timeout=10)

        assert _flags(queued) == {name: name == first for name in _ACTIONS}


def test_killed_queued_task_completes(qtbot, executor_context_factory):
    """Kill completes the future of a queued task right away."""
    with executor_context_factory(workers=1) as (kind, executor):
        if kind != "process":
            pytest.skip("kill is only supported in a subprocess")

        with qtbot.wait_signal(executor.started, timeout=10_000):
            blocker = executor.submit_task(AddTask, inputs={"a": 1, "delay": 2})

        with qtbot.wait_signal(executor.finished, timeout=10_000) as signal_blocker:
            queued = executor.submit_task(AddTask, inputs={"a": 2})

            assert queued.kill()
            assert queued.done()
            assert not blocker.done()
            with pytest.raises(TaskKilledError, match="killed before it started"):
                queued.result(timeout=0)

        assert signal_blocker.args[0] is queued

        with qtbot.wait_signal(executor.finished, timeout=10_000):
            assert blocker.result(timeout=10)["result"].value == 1


def test_failed_watch_ends_execution(qtbot, executor_context_factory, monkeypatch):
    """When the relay fails to start, the submission raises, the execution ends
    with `cancelled` and `finished`, and the executor stays usable."""
    with executor_context_factory(workers=1) as (kind, executor):
        if kind != "process":
            pytest.skip("only the process backend watches the task")

        def _failing_watch(*args, **kwargs) -> None:
            raise RuntimeError("cannot start the relay")

        with assert_none_emitted(
            qtbot,
            executor.aboutToStart,
            executor.started,
            executor.succeeded,
            executor.failed,
        ), qtbot.wait_signals(
            [executor.submitted, executor.cancelled, executor.finished],
            timeout=10_000,
            order="strict",
        ) as signals_blocker:
            # Last resort: starting a thread cannot be made to fail otherwise.
            with monkeypatch.context() as patch:
                patch.setattr(ProcessTaskController, "watch", _failing_watch)
                with pytest.raises(RuntimeError, match="cannot start the relay"):
                    executor.submit_task(AddTask, inputs={"a": 1})

        assert signals_blocker.all_signals_and_args[-1].args[0].cancelled()

        with qtbot.wait_signal(executor.finished, timeout=35_000):
            future = executor.submit_task(AddTask, inputs={"a": 2})
            assert future.result(timeout=30)["result"].value == 2


def test_finished_task(qtbot, executor_context_factory):
    """No action has an effect on a finished task."""
    with executor_context_factory() as (_, executor):
        with assert_none_emitted(
            qtbot,
            *(
                getattr(executor, name)
                for name in _OUTCOME_SIGNALS
                if name != "succeeded"
            ),
        ), qtbot.wait_signals(
            [
                executor.submitted,
                executor.aboutToStart,
                executor.started,
                executor.succeeded,
                executor.finished,
            ],
            timeout=10_000,
            order="strict",
        ):
            future = executor.submit_task(AddTask, inputs={"a": 1})
            assert future.result(timeout=10)["result"].value == 1

            for action in _ACTIONS:
                assert not getattr(future, action)(), action

        assert future.result()["result"].value == 1
        assert _flags(future) == dict.fromkeys(_ACTIONS, False)


def _flags(future: TaskFuture) -> Dict[str, bool]:
    """Which action had an effect, according to the future."""
    return {
        "cancel": future.cancelled(),
        "request_stop": future.stop_requested(),
        "abort": future.aborted(),
        "kill": future.killed(),
    }
