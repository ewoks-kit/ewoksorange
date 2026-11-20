import threading

from ...gui.concurrency.executor import SubmitPolicy
from .tasks import AddTask
from .utils import assert_signal_counts


def test_drop_if_busy(qtbot, executor_context_factory):
    with executor_context_factory(SubmitPolicy.DROP_IF_BUSY, workers=1) as (
        kind,
        executor,
    ):
        inputs = {"a": 1, "delay": 2}
        thread = None
        nb_extra = 4

        with assert_signal_counts(
            qtbot,
            executor,
            submitted=1,
            aboutToStart=1,
            started=1,
            succeeded=1,
            finished=1,
            ignored=nb_extra,
        ), qtbot.wait_signals(
            [executor.succeeded, executor.finished], timeout=15_000, order="strict"
        ):
            with qtbot.wait_signals(
                [executor.submitted, executor.aboutToStart, executor.started],
                timeout=10_000,
                order="strict",
            ) as first_signals_blocker:
                if kind == "sync":
                    # submit_task() blocks until the task finishes, so it must
                    # run on its own thread to still be "busy" when the
                    # second is submitted.
                    thread = threading.Thread(
                        target=executor.submit_task,
                        args=(AddTask,),
                        kwargs={"inputs": inputs},
                    )
                    thread.start()
                else:
                    executor.submit_task(AddTask, inputs=inputs)

            first = first_signals_blocker.all_signals_and_args[0].args[0]

            with qtbot.wait_signals(
                [executor.ignored] * nb_extra, timeout=10_000, order="strict"
            ):
                # Every submission while busy is dropped, not just the first
                # excess one.
                extra = [
                    executor.submit_task(AddTask, inputs={"a": i})
                    for i in range(nb_extra)
                ]
                assert extra == [None] * len(extra)

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
        with assert_signal_counts(
            qtbot,
            executor,
            submitted=nb_submits,
            aboutToStart=nb_submits,
            started=nb_submits,
            succeeded=nb_submits,
            finished=nb_submits,
        ):
            for i in range(nb_submits):
                futures.append(
                    executor.submit_task(AddTask, inputs={"a": i, "delay": 0.2})
                )

            for future in futures:
                future.result(timeout=10)
