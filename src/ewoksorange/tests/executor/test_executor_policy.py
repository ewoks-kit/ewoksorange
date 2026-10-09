import threading

from ...gui.concurrency.executor import SubmitPolicy
from .tasks import AddTask


def test_drop_if_busy(qtbot, executor_context_factory):
    with executor_context_factory(SubmitPolicy.DROP_IF_BUSY, workers=1) as (
        kind,
        executor,
    ):
        inputs = {"a": 1, "delay": 2}
        with qtbot.wait_signals(
            [executor.submitted, executor.started], timeout=10_000, order="strict"
        ) as first_signals_blocker:
            thread = None
            if kind == "sync":
                # submit_task() blocks until the task finishes, so it must run
                # on its own thread to still be "busy" when the second is submitted.
                thread = threading.Thread(
                    target=executor.submit_task,
                    args=(AddTask,),
                    kwargs={"inputs": inputs},
                )
                thread.start()
            else:
                executor.submit_task(AddTask, inputs=inputs)

        first = first_signals_blocker.all_signals_and_args[0].args[0]

        nb_extra = 4
        with qtbot.wait_signals(
            [executor.ignored] * nb_extra, timeout=10_000, order="strict"
        ):
            # Every submission while busy is dropped, not just the first excess one.
            extra = [
                executor.submit_task(AddTask, inputs={"a": i}) for i in range(nb_extra)
            ]
            assert extra == [None] * len(extra)

        with qtbot.wait_signals(
            [executor.succeeded, executor.finished], timeout=15_000, order="strict"
        ):
            first.result(timeout=10)

        if thread is not None:
            thread.join(timeout=10)


def test_always_queue(qtbot, executor_context_factory):

    with executor_context_factory(SubmitPolicy.ALWAYS, workers=1) as (
        _,
        executor,
    ):
        futures = []

        nb_submits = 3
        with qtbot.wait_signals(
            [
                executor.submitted,
                executor.started,
                executor.succeeded,
                executor.finished,
            ]
            * nb_submits,
            timeout=35_000,
        ):
            for i in range(nb_submits):
                futures.append(
                    executor.submit_task(AddTask, inputs={"a": i, "delay": 0.2})
                )

            for future in futures:
                future.result(timeout=10)
