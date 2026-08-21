"""Configure task execution directly on `OWEwoksBaseWidget`."""

import multiprocessing
import os
import threading
import time
from typing import List

import numpy
import pytest
from ewokscore.task import Task

from ...gui.concurrency.executor import Concurrency
from ...gui.concurrency.executor import SubmitPolicy
from ...gui.owwidgets.base import OWEwoksBaseWidget
from ...gui.owwidgets.meta import _parse_concurrency
from ...gui.owwidgets.meta import _parse_max_workers
from ...gui.owwidgets.meta import _parse_mp_context
from ...gui.owwidgets.meta import _parse_submit_policy
from ...gui.owwidgets.meta import ow_build_opts
from ...gui.owwidgets.nothread import OWEwoksWidgetNoThread
from ...gui.owwidgets.threaded import OWEwoksWidgetOneThread
from ...gui.owwidgets.threaded import OWEwoksWidgetOneThreadPerRun
from ...gui.owwidgets.threaded import OWEwoksWidgetWithTaskStack
from ...gui.qt_utils.app import wait_until

# The process backend pickles the task class by reference, so the child process
# imports its module. These are Qt-free, unlike this test module.
from ..executor.tasks import PidTask
from ..executor.tasks import ProgressTask


class Sequential(
    Task, input_names=["value", "sleep"], output_names=["value", "time", "thread_id"]
):
    def run(self):
        time.sleep(self.inputs.sleep)
        self.outputs.time = time.perf_counter()
        self.outputs.value = self.inputs.value
        self.outputs.thread_id = threading.get_ident()


class Blocking(Task, input_names=["release"], output_names=["value"]):
    def run(self):
        assert self.inputs.release.wait(timeout=10)
        self.outputs.value = 1


class OWDefault(OWEwoksBaseWidget, **ow_build_opts, ewokstaskclass=Sequential):
    name = "test_OW_default"


class OWSync(
    OWEwoksBaseWidget,
    **ow_build_opts,
    ewokstaskclass=Sequential,
    concurrency=Concurrency.SYNC,
):
    name = "test_OW_sync"


class OWPool(
    OWEwoksBaseWidget,
    **ow_build_opts,
    ewokstaskclass=Sequential,
    concurrency="thread",
    max_workers=4,
):
    name = "test_OW_pool"


class OWDropIfBusy(
    OWEwoksBaseWidget,
    **ow_build_opts,
    ewokstaskclass=Blocking,
    max_workers=1,
    submit_policy="drop_if_busy",
):
    name = "test_OW_drop"


class OWProcess(
    OWEwoksBaseWidget,
    **ow_build_opts,
    ewokstaskclass=PidTask,
    concurrency="process",
    max_workers=1,
):
    name = "test_OW_process"


class OWProcessProgress(
    OWEwoksBaseWidget,
    **ow_build_opts,
    ewokstaskclass=ProgressTask,
    concurrency=Concurrency.PROCESS,
    max_workers=1,
):
    name = "test_OW_process_progress"


class OWProcessPlatformContext(
    OWEwoksBaseWidget,
    **ow_build_opts,
    ewokstaskclass=PidTask,
    concurrency="process",
    max_workers=1,
    mp_context=None,
):
    name = "test_OW_process_platform_context"


def test_default_configuration():
    """Without class arguments: unbounded workers in a single background thread."""
    assert OWDefault._CONCURRENCY is Concurrency.THREAD
    assert OWDefault._MAX_WORKERS is None
    assert OWDefault._SUBMIT_POLICY is SubmitPolicy.ALWAYS
    assert OWDefault._MP_CONTEXT.get_start_method() == "spawn"


@pytest.mark.parametrize(
    "widget_class,concurrency,max_workers,submit_policy",
    [
        (OWEwoksWidgetNoThread, Concurrency.SYNC, None, SubmitPolicy.ALWAYS),
        (OWEwoksWidgetOneThread, Concurrency.THREAD, 1, SubmitPolicy.DROP_IF_BUSY),
        (OWEwoksWidgetOneThreadPerRun, Concurrency.THREAD, None, SubmitPolicy.ALWAYS),
        (OWEwoksWidgetWithTaskStack, Concurrency.THREAD, 1, SubmitPolicy.ALWAYS),
    ],
)
def test_sub_classes_are_configurations(
    widget_class, concurrency, max_workers, submit_policy
):
    """The pre-existing classes only differ from the base class by configuration."""
    assert widget_class.__bases__ == (OWEwoksBaseWidget,)
    assert widget_class._CONCURRENCY is concurrency
    assert widget_class._MAX_WORKERS == max_workers
    assert widget_class._SUBMIT_POLICY is submit_policy


def test_metaclass_only_sets_options_that_are_provided():
    class OWParent(
        OWEwoksBaseWidget,
        **ow_build_opts,
        ewokstaskclass=Sequential,
        concurrency="thread",
        max_workers=4,
        submit_policy="drop_if_busy",
        mp_context="spawn",
    ):
        name = "test_OW_parent"

    # No execution class arguments provided: nothing should be written to
    # OWChild's own namespace.
    class OWChild(OWParent, **ow_build_opts):
        name = "test_OW_child"

    for attr in ("_CONCURRENCY", "_MAX_WORKERS", "_SUBMIT_POLICY", "_MP_CONTEXT"):
        assert attr not in vars(OWChild)

    # Values are still visible, inherited from OWParent.
    assert OWChild._CONCURRENCY is Concurrency.THREAD
    assert OWChild._MAX_WORKERS == 4
    assert OWChild._SUBMIT_POLICY is SubmitPolicy.DROP_IF_BUSY
    assert OWChild._MP_CONTEXT is OWParent._MP_CONTEXT

    # Only the provided argument is written to OWGrandchild's own namespace.
    class OWGrandchild(OWChild, **ow_build_opts, max_workers=2):
        name = "test_OW_grandchild"

    assert vars(OWGrandchild)["_MAX_WORKERS"] == 2
    for attr in ("_CONCURRENCY", "_SUBMIT_POLICY", "_MP_CONTEXT"):
        assert attr not in vars(OWGrandchild)

    # The untouched options still climb the MRO up to OWParent's values.
    assert OWGrandchild._CONCURRENCY is Concurrency.THREAD
    assert OWGrandchild._SUBMIT_POLICY is SubmitPolicy.DROP_IF_BUSY
    assert OWGrandchild._MP_CONTEXT is OWParent._MP_CONTEXT


def test_configure_sync(ewoksorange_qtapp):
    """`concurrency="sync"` executes in the calling thread."""
    widget = OWSync()
    try:
        widget.set_dynamic_input("value", 1)
        widget.set_dynamic_input("sleep", 0)

        future = widget.execute_ewoks_task()
        assert future is not None

        # Everything already happened when the submission returns.
        assert future.done()
        assert not widget.has_pending_task()
        assert future.exception() is None
        assert widget.get_task_output_values()["value"] == 1
        assert widget.get_task_output_values()["thread_id"] == threading.get_ident()
    finally:
        widget.onDeleteWidget()


def test_configure_pool(ewoksorange_qtapp):
    """`max_workers>1` executes tasks concurrently in background threads."""
    widget = OWPool()
    try:
        sleep_seconds = 0.5
        futures = []
        for value in range(4):
            widget.set_dynamic_input("value", value)
            widget.set_dynamic_input("sleep", sleep_seconds)
            futures.append(widget.execute_ewoks_task())

        times = []
        for future in futures:
            outputs = future.result(timeout=10)
            times.append(outputs["time"].value)
            assert outputs["thread_id"].value != threading.get_ident()

        assert (numpy.diff(sorted(times)) < 0.5 * sleep_seconds).all(), (
            "not executed in parallel"
        )
    finally:
        widget.onDeleteWidget()


def test_configure_drop_if_busy(ewoksorange_qtapp):
    """`submit_policy="drop_if_busy"` refuses submissions while a task runs."""
    widget = OWDropIfBusy()
    release = threading.Event()
    try:
        widget.set_dynamic_input("release", release)

        first = widget.execute_ewoks_task()
        assert first is not None

        assert widget.execute_ewoks_task() is None
        assert widget.execute_ewoks_task_without_propagation() is None

        release.set()
        assert first.result(timeout=10)["value"].value == 1
    finally:
        release.set()
        widget.onDeleteWidget()


def test_configure_mp_context():
    """`mp_context` accepts a `multiprocessing` context, a start method name or
    `None` for the platform default."""
    assert OWProcess._MP_CONTEXT.get_start_method() == "spawn"
    assert OWProcessPlatformContext._MP_CONTEXT is None

    # "spawn" is the only start method available on all platforms.
    context = multiprocessing.get_context("spawn")

    class OWContext(
        OWEwoksBaseWidget,
        **ow_build_opts,
        ewokstaskclass=PidTask,
        concurrency="process",
        mp_context=context,
    ):
        name = "test_OW_mp_context"

    assert OWContext._MP_CONTEXT is context


@pytest.mark.parametrize("widget_class", [OWProcess, OWProcessPlatformContext])
def test_configure_process(ewoksorange_qtapp, widget_class):
    """`concurrency="process"` executes in another process."""
    widget = widget_class()
    try:
        widget.set_dynamic_input("value", 3)

        future = widget.execute_ewoks_task()
        assert future is not None

        assert wait_until(lambda: not widget.has_pending_task(), timeout=120)
        assert future.exception() is None

        outputs = widget.get_task_output_values()
        assert outputs["value"] == 3
        assert outputs["pid"] != os.getpid()
    finally:
        widget.onDeleteWidget()


def test_configure_process_progress(ewoksorange_qtapp):
    """Task progress is relayed from the worker process to the progress bar."""
    percentages = [10, 40, 100]

    widget = OWProcessProgress()
    received: List[int] = []
    # The public Orange method the widget's progress handler calls.
    # `progressBarInit()` passes a second `processEvents` argument on some
    # Orange forks, so accept and ignore extra arguments.
    widget.progressBarSet = lambda value, *args, **kwargs: received.append(value)
    try:
        widget.set_dynamic_input("percentages", percentages)

        future = widget.execute_ewoks_task()
        assert future is not None

        assert wait_until(lambda: not widget.has_pending_task(), timeout=120)
        assert future.exception() is None

        assert widget.get_task_output_values()["pid"] != os.getpid()
        # `progressBarInit` reports 0 before the task starts.
        assert received == [0] + percentages
    finally:
        widget.onDeleteWidget()


def test_configure_propagation(ewoksorange_qtapp):
    """Propagation is per submission, also when executing synchronously."""
    propagated = []

    class OWPropagate(
        OWEwoksBaseWidget,
        **ow_build_opts,
        ewokstaskclass=Sequential,
        concurrency="sync",
    ):
        name = "test_OW_propagate"

        def trigger_downstream(self):
            propagated.append("trigger_downstream")

        def clear_downstream(self):
            propagated.append("clear_downstream")

    widget = OWPropagate()
    try:
        widget.set_dynamic_input("value", 1)
        widget.set_dynamic_input("sleep", 0)

        widget.execute_ewoks_task_without_propagation()
        assert propagated == []

        widget.execute_ewoks_task()
        assert propagated == ["trigger_downstream"]
    finally:
        widget.onDeleteWidget()


@pytest.mark.parametrize("concurrency", ["threads", "", 1, None])
def test_invalid_concurrency(concurrency):
    with pytest.raises(ValueError, match="concurrency"):

        class OWInvalid(
            OWEwoksBaseWidget,
            **ow_build_opts,
            ewokstaskclass=Sequential,
            concurrency=concurrency,
        ):
            name = "test_OW_invalid"


@pytest.mark.parametrize("max_workers", [0, -1, 1.5, "1", True])
def test_invalid_max_workers(max_workers):
    with pytest.raises(ValueError, match="max_workers"):

        class OWInvalid(
            OWEwoksBaseWidget,
            **ow_build_opts,
            ewokstaskclass=Sequential,
            max_workers=max_workers,
        ):
            name = "test_OW_invalid"


@pytest.mark.parametrize("submit_policy", ["never", 1, None])
def test_invalid_submit_policy(submit_policy):
    with pytest.raises(ValueError, match="submit_policy"):

        class OWInvalid(
            OWEwoksBaseWidget,
            **ow_build_opts,
            ewokstaskclass=Sequential,
            submit_policy=submit_policy,
        ):
            name = "test_OW_invalid"


@pytest.mark.parametrize("mp_context", ["threads", "", 1])
def test_invalid_mp_context(mp_context):
    with pytest.raises(ValueError, match="mp_context"):

        class OWInvalid(
            OWEwoksBaseWidget,
            **ow_build_opts,
            ewokstaskclass=Sequential,
            mp_context=mp_context,
        ):
            name = "test_OW_invalid"


@pytest.mark.parametrize(
    "concurrency,expected",
    [
        (Concurrency.SYNC, Concurrency.SYNC),
        (Concurrency.THREAD, Concurrency.THREAD),
        (Concurrency.PROCESS, Concurrency.PROCESS),
        ("sync", Concurrency.SYNC),
        ("thread", Concurrency.THREAD),
        ("process", Concurrency.PROCESS),
        ("THREAD", Concurrency.THREAD),
        ("threads", ValueError("concurrency")),
        ("", ValueError("concurrency")),
        (1, ValueError("concurrency")),
        (None, ValueError("concurrency")),
    ],
)
def test_parse_concurrency(concurrency, expected):
    if isinstance(expected, Exception):
        with pytest.raises(type(expected), match=str(expected)):
            _parse_concurrency(concurrency)
    else:
        assert _parse_concurrency(concurrency) is expected


@pytest.mark.parametrize(
    "max_workers,expected",
    [
        (None, None),
        (1, 1),
        (4, 4),
        (0, ValueError("max_workers")),
        (-1, ValueError("max_workers")),
        (1.5, ValueError("max_workers")),
        ("1", ValueError("max_workers")),
        (True, ValueError("max_workers")),
    ],
)
def test_parse_max_workers(max_workers, expected):
    if isinstance(expected, Exception):
        with pytest.raises(type(expected), match=str(expected)):
            _parse_max_workers(max_workers)
    else:
        assert _parse_max_workers(max_workers) == expected


@pytest.mark.parametrize(
    "submit_policy,expected",
    [
        (SubmitPolicy.ALWAYS, SubmitPolicy.ALWAYS),
        (SubmitPolicy.DROP_IF_BUSY, SubmitPolicy.DROP_IF_BUSY),
        ("always", SubmitPolicy.ALWAYS),
        ("drop_if_busy", SubmitPolicy.DROP_IF_BUSY),
        ("ALWAYS", SubmitPolicy.ALWAYS),
        ("never", ValueError("submit_policy")),
        (1, ValueError("submit_policy")),
        (None, ValueError("submit_policy")),
    ],
)
def test_parse_submit_policy(submit_policy, expected):
    if isinstance(expected, Exception):
        with pytest.raises(type(expected), match=str(expected)):
            _parse_submit_policy(submit_policy)
    else:
        assert _parse_submit_policy(submit_policy) is expected


_SPAWN_CONTEXT = multiprocessing.get_context("spawn")


@pytest.mark.parametrize(
    "mp_context,expected",
    [
        (None, None),
        ("spawn", _SPAWN_CONTEXT),
        (_SPAWN_CONTEXT, _SPAWN_CONTEXT),
        ("threads", ValueError("mp_context")),
        ("", ValueError("mp_context")),
        (1, ValueError("mp_context")),
    ],
)
def test_parse_mp_context(mp_context, expected):
    if isinstance(expected, Exception):
        with pytest.raises(type(expected), match=str(expected)):
            _parse_mp_context(mp_context)
    else:
        assert _parse_mp_context(mp_context) is expected
