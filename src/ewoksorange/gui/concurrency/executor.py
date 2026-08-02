from __future__ import annotations

import logging
import multiprocessing
import multiprocessing.managers
import weakref
from concurrent import futures
from enum import Enum
from enum import auto
from threading import Event
from threading import Lock
from typing import Any
from typing import Callable
from typing import List
from typing import Optional
from typing import Type

from AnyQt.QtCore import QObject
from AnyQt.QtCore import Signal
from ewokscore.task import Task

from . import _controllers
from . import _runners
from .future import TaskFuture

_logger = logging.getLogger(__name__)


class SubmitPolicy(Enum):
    ALWAYS = auto()
    DROP_IF_BUSY = auto()


class EwoksExecutor(QObject):
    """Qt-aware executor for ewoks tasks.

    Wraps a `concurrent.futures.Executor` (thread, process or None) and emits Qt
    signals on task lifecycle events. Returns TaskFuture objects that support
    both native future cancellation (cancel()) and ewoks task abort (abort()).
    """

    submitted = Signal(TaskFuture)
    """Emitted when a task is submitted."""

    started = Signal(TaskFuture)
    """Emitted when a task starts executing."""

    succeeded = Signal(TaskFuture)
    """Emitted when a task finishes successfully."""

    failed = Signal(TaskFuture)
    """Emitted when a task raises an exception."""

    ignored = Signal()
    """Emitted when a task submission is ignored due to the DROP_IF_BUSY policy."""

    aborted = Signal(TaskFuture)
    """Emitted when a task was aborted."""

    finished = Signal(TaskFuture)
    """Emitted when a task finishes (success, failure, or abort)."""

    def __init__(
        self,
        executor: Optional[futures.Executor],
        policy: SubmitPolicy = SubmitPolicy.ALWAYS,
    ):
        super().__init__()

        self._executor = executor
        self._policy = policy
        self._running = 0
        self._lock = Lock()

        self._as_process = isinstance(executor, futures.ProcessPoolExecutor)

        self._manager: Optional[multiprocessing.managers.SyncManager] = None

    def submit_task(
        self, task_class: Type[Task], **task_kwargs
    ) -> Optional[TaskFuture]:

        with self._lock:
            if self._policy is SubmitPolicy.DROP_IF_BUSY and self._running:
                _logger.warning("Submission ignored: executor busy")
                self.ignored.emit()
                return None

            self._running += 1

        if self._executor is None:
            return self._submit_sync(task_class, task_kwargs)

        if self._as_process:
            return self._submit_process(task_class, task_kwargs)

        return self._submit_thread(task_class, task_kwargs)

    def _submit_sync(self, task_class: Type[Task], task_kwargs: dict) -> TaskFuture:
        controller = _controllers.SyncTaskController()
        self_ref = weakref.ref(self)
        holder: List[Optional[TaskFuture]] = [None]
        runner = _runners.SyncTaskRunner(
            task_class,
            task_kwargs,
            controller,
            on_started=lambda: _emit_started(self_ref, holder),
        )

        raw_future = futures.Future()

        return self._finalize_submission(
            raw_future,
            controller,
            holder,
            self_ref,
            after_submitted=lambda: _sync_submit(runner, raw_future),
        )

    def _submit_thread(self, task_class: Type[Task], task_kwargs: dict) -> TaskFuture:
        controller = _controllers.ThreadTaskController()
        ready_event = Event()
        self_ref = weakref.ref(self)
        holder: List[Optional[TaskFuture]] = [None]
        runner = _runners.ThreadTaskRunner(
            task_class,
            task_kwargs,
            controller,
            ready_event,
            on_started=lambda: _emit_started(self_ref, holder),
        )

        raw_future = self._executor.submit(runner)

        return self._finalize_submission(
            raw_future, controller, holder, self_ref, after_submitted=ready_event.set
        )

    def _submit_process(self, task_class: Type[Task], task_kwargs: dict) -> TaskFuture:
        manager = self._get_manager()

        ready_event = manager.Event()
        started_queue = manager.Queue()
        abort_event = manager.Event()
        aborted_event = manager.Event()

        controller = _controllers.ProcessTaskController(
            abort_event, aborted_event, started_queue
        )
        runner = _runners.ProcessTaskRunner(
            task_class,
            task_kwargs,
            ready_event,
            started_queue,
            abort_event,
            aborted_event,
        )

        self_ref = weakref.ref(self)
        holder: List[Optional[TaskFuture]] = [None]
        controller.watch_started(lambda: _emit_started(self_ref, holder))

        raw_future = self._executor.submit(runner)

        return self._finalize_submission(
            raw_future, controller, holder, self_ref, after_submitted=ready_event.set
        )

    def _finalize_submission(
        self,
        raw_future: futures.Future,
        controller: _controllers.TaskController,
        holder: List[Optional[TaskFuture]],
        self_ref: weakref.ReferenceType["EwoksExecutor"],
        after_submitted: Callable[[], None],
    ) -> TaskFuture:
        task_future = TaskFuture(raw_future, controller)

        holder[0] = task_future

        self.submitted.emit(task_future)

        after_submitted()

        raw_future.add_done_callback(lambda f: _done_callback(self_ref, f, task_future))

        return task_future

    def _get_manager(self) -> multiprocessing.managers.SyncManager:
        if self._manager is None:
            self._manager = multiprocessing.Manager()

        return self._manager

    def _handle_done(self, raw_future: futures.Future, task_future: TaskFuture) -> None:
        with self._lock:
            self._running -= 1

        if raw_future.cancelled():
            return

        if task_future.aborted():
            self.aborted.emit(task_future)

        try:
            raw_future.result()
        except Exception:
            self.failed.emit(task_future)
        else:
            self.succeeded.emit(task_future)
        finally:
            self.finished.emit(task_future)

    def shutdown(self, wait: bool = False) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=wait)

        if self._manager is not None:
            self._manager.shutdown()
            self._manager = None


def _done_callback(
    executor_ref: weakref.ReferenceType[EwoksExecutor],
    raw_future: futures.Future,
    task_future: TaskFuture,
) -> None:
    executor = executor_ref()
    if executor is not None:
        executor._handle_done(raw_future, task_future)


def _emit_started(
    executor_ref: weakref.ReferenceType[EwoksExecutor],
    holder: List[Optional[TaskFuture]],
) -> None:
    executor = executor_ref()
    if executor is not None and holder and holder[0] is not None:
        executor.started.emit(holder[0])


def _sync_submit(fn: Callable[[], Any], raw_future: futures.Future) -> None:
    """Run `fn` and store its outcome in `raw_future`."""
    # `ThreadPoolExecutor`/`ProcessPoolExecutor` already do this internally
    # (via `set_running_or_notify_cancel()`) before invoking a submitted
    # callable, honoring a `cancel()` that raced with the start of execution
    # instead of silently overwriting it. The sync case has no real
    # `Executor` behind it doing that for us, so it's done here explicitly.
    if not raw_future.set_running_or_notify_cancel():
        return

    try:
        result = fn()
    except BaseException as exc:
        raw_future.set_exception(exc)
    else:
        raw_future.set_result(result)
