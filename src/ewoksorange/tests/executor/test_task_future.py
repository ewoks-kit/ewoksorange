import threading

from ...gui.concurrency.executor import TaskFuture
from .tasks import AddTask


def test_running_and_done(qtbot, executor_context_factory):
    with executor_context_factory() as (kind, executor):
        inputs = {"a": 1, "delay": 1}
        thread = None
        with qtbot.wait_signal(executor.started) as signal_blocker:
            if kind == "sync":
                # submit_task() blocks until the task finishes, so it must run
                # on its own thread to observe it mid-flight below.
                thread = threading.Thread(
                    target=executor.submit_task,
                    args=(AddTask,),
                    kwargs={"inputs": inputs},
                )
                thread.start()
            else:
                executor.submit_task(AddTask, inputs=inputs)

        assert len(signal_blocker.args) == 1
        future = signal_blocker.args[0]
        assert isinstance(future, TaskFuture)

        assert future.running()
        assert not future.done()

        future.result(timeout=10)

        assert future.done()
        assert not future.running()

        if thread is not None:
            thread.join(timeout=10)


def test_cancelled(qtbot, executor_context_factory):
    """`cancelled()` reflects whether `cancel()` actually succeeded."""
    with executor_context_factory() as (kind, executor):
        inputs = {"a": 1}
        if kind == "sync":
            # submit_task() blocks, so cancel() can only ever race with (or
            # arrive after) completion: it never truly finds a queued task.
            thread = threading.Thread(
                target=executor.submit_task, args=(AddTask,), kwargs={"inputs": inputs}
            )
            with qtbot.wait_signal(executor.succeeded) as signal_blocker:
                thread.start()

            assert len(signal_blocker.args) == 1
            future = signal_blocker.args[0]
            assert isinstance(future, TaskFuture)

            assert not future.cancel()
            assert not future.cancelled()
            thread.join(timeout=10)
        else:
            with qtbot.wait_signal(executor.finished):
                future = executor.submit_task(AddTask, inputs=inputs)
                future.cancel()
            # Whether cancel() wins the race with the worker picking up the
            # task is not guaranteed; cancelled() must simply agree with it.
            assert future.cancelled() == future.cancel()


def test_add_done_callback(qtbot, executor_context_factory):
    with executor_context_factory() as (_, executor):
        received = {}

        future = executor.submit_task(AddTask, inputs={"a": 1, "b": 2})
        # add_done_callback() forwards to the wrapped concurrent.futures.Future,
        # so the callback receives that raw future, not the TaskFuture itself.
        future.add_done_callback(
            lambda raw_future: received.update(raw_future=raw_future)
        )
        qtbot.wait_until(lambda: "raw_future" in received, timeout=10_000)

        assert received["raw_future"].result()["result"].value == 3
