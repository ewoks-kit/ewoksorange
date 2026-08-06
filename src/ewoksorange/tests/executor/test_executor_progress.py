"""Ewoks task progress reaches the caller for every execution backend."""

import os
from typing import List

from ...gui.qt_utils.progress import QProgress
from .tasks import PidTask
from .tasks import ProgressTask


def test_progress(qtapp, executor_context_factory):
    """The caller's progress object receives every value the task reports.

    `QProgress` is a `QObject` and therefore not picklable, which the process
    backend has to work around without the caller noticing.
    """
    percentages = [10, 40, 100]

    with executor_context_factory() as (kind, executor, recorder):
        progress = QProgress()
        received: List[int] = []
        progress.sigProgressChanged.connect(received.append)

        future = executor.submit_task(
            ProgressTask, inputs={"percentages": percentages}, progress=progress
        )

        result = future.result(timeout=30)

        # `finished` is only emitted once all progress values were relayed, so
        # no polling on `received` is needed here.
        recorder.wait_for("finished", 1)

        assert received == percentages
        assert progress.progress == 100

        if kind == "process":
            assert result["pid"].value != os.getpid()
        else:
            assert result["pid"].value == os.getpid()


def test_progress_for_task_without_progress_support(qtapp, executor_context_factory):
    """A `progress` argument for a plain `Task` is dropped, not forwarded.

    For the process backend it must be dropped before pickling, otherwise
    submitting any `Task` with a Qt bound progress object fails.
    """
    with executor_context_factory() as (kind, executor, recorder):
        progress = QProgress()
        received: List[int] = []
        progress.sigProgressChanged.connect(received.append)

        future = executor.submit_task(PidTask, inputs={"value": 3}, progress=progress)

        result = future.result(timeout=30)

        recorder.wait_for("finished", 1)
        recorder.assert_counts(submitted=1, started=1, succeeded=1, finished=1)

        assert result["value"].value == 3
        assert received == []

        if kind == "process":
            assert result["pid"].value != os.getpid()
        else:
            assert result["pid"].value == os.getpid()
