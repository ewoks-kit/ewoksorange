import threading

from ...gui.qt_utils.app import QtEvent
from .tasks import AddTask


def test_running_and_done(qtapp, executor_context_factory):
    with executor_context_factory() as (kind, executor, recorder):
        inputs = {"a": 1, "delay": 1}
        thread = None
        if kind == "sync":
            # submit_task() blocks until the task finishes, so it must run
            # on its own thread to observe it mid-flight below.
            thread = threading.Thread(
                target=executor.submit_task, args=(AddTask,), kwargs={"inputs": inputs}
            )
            thread.start()
        else:
            executor.submit_task(AddTask, inputs=inputs)

        future = recorder.wait_future("started")

        assert future.running()
        assert not future.done()

        future.result(timeout=10)

        assert future.done()
        assert not future.running()

        if thread is not None:
            thread.join(timeout=10)


def test_cancelled(qtapp, executor_context_factory):
    """`cancelled()` reflects whether `cancel()` actually succeeded."""
    with executor_context_factory() as (kind, executor, recorder):
        inputs = {"a": 1}
        thread = None
        if kind == "sync":
            # submit_task() blocks, so cancel() can only ever race with (or
            # arrive after) completion: it never truly finds a queued task.
            thread = threading.Thread(
                target=executor.submit_task, args=(AddTask,), kwargs={"inputs": inputs}
            )
            thread.start()
            future = recorder.wait_future("succeeded")
            assert not future.cancel()
            assert not future.cancelled()
            thread.join(timeout=10)
        else:
            future = executor.submit_task(AddTask, inputs=inputs)
            future.cancel()
            recorder.wait_for("finished", 1)
            # Whether cancel() wins the race with the worker picking up the
            # task is not guaranteed; cancelled() must simply agree with it.
            assert future.cancelled() == future.cancel()


def test_add_done_callback(qtapp, executor_context_factory):
    with executor_context_factory() as (_, executor, recorder):
        done = QtEvent()
        received = {}

        future = executor.submit_task(AddTask, inputs={"a": 1, "b": 2})
        # add_done_callback() forwards to the wrapped concurrent.futures.Future,
        # so the callback receives that raw future, not the TaskFuture itself.
        future.add_done_callback(
            lambda raw_future: (received.update(raw_future=raw_future), done.set())
        )

        assert done.wait(timeout=10)
        assert received["raw_future"].result()["result"].value == 3
