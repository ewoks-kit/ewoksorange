from __future__ import annotations

import logging
import multiprocessing
import multiprocessing.context
import multiprocessing.managers
import weakref
from concurrent import futures
from enum import Enum
from enum import auto
from queue import Queue
from threading import Event
from threading import Lock
from threading import Thread
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Type

from AnyQt.QtCore import QObject
from AnyQt.QtCore import Signal
from ewokscore import TaskWithProgress
from ewokscore.task import Task
from ewokscore.variable import VariableContainer

from . import _controllers
from . import _progress
from . import _runners
from .future import TaskFuture

_logger = logging.getLogger(__name__)


class SubmitPolicy(Enum):
    ALWAYS = auto()
    DROP_IF_BUSY = auto()


class Concurrency(Enum):
    """How an :class:`EwoksExecutor` executes ewoks tasks."""

    SYNC = auto()
    """In the calling thread."""

    THREAD = auto()
    """In a thread pool."""

    PROCESS = auto()
    """In a process pool."""


def create_pool_executor(
    concurrency: Concurrency,
    max_workers: Optional[int] = None,
    mp_context: Optional[multiprocessing.context.BaseContext] = None,
) -> Optional[futures.Executor]:
    """Create the `concurrent.futures` executor for a given concurrency.

    :param concurrency: The execution backend.
    :param max_workers: Maximum number of workers, `None` for the pool default.
                        Ignored for `Concurrency.SYNC`.
    :param mp_context: Multiprocessing context, only used for `Concurrency.PROCESS`.
    :return: The executor, or `None` for `Concurrency.SYNC`.
    """
    if concurrency is Concurrency.SYNC:
        return None
    if concurrency is Concurrency.PROCESS:
        return futures.ProcessPoolExecutor(
            max_workers=max_workers, mp_context=mp_context
        )
    return futures.ThreadPoolExecutor(max_workers=max_workers)


class EwoksExecutor(QObject):
    """Qt-aware executor for ewoks tasks.

    Wraps a `concurrent.futures.Executor` (thread, process or None) and emits Qt
    signals on task lifecycle events. Returns TaskFuture objects that support
    both native future cancellation (cancel()) and ewoks task abort (abort()).
    Their result is the executed task's
    :class:`~ewokscore.variable.VariableContainer` of output variables.
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
        mp_context: Optional[multiprocessing.context.BaseContext] = None,
    ):
        """
        :param executor: Wrapped executor, `None` to execute in the calling thread.
        :param policy: What to do with submissions while the executor is busy.
        :param mp_context: Multiprocessing context used for the IPC manager. Provide
                           the context of `executor` so the manager process is created
                           with the same start method.
        """
        super().__init__()

        self._executor = executor
        self._policy = policy
        self._mp_context = mp_context
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

    def _submit_sync(
        self, task_class: Type[Task], task_kwargs: Dict[str, Any]
    ) -> TaskFuture:
        controller = _controllers.SyncTaskController()
        self_ref = weakref.ref(self)
        holder: List[Optional[TaskFuture]] = [None]
        task_kwargs = self._handle_progess_arg(task_class, task_kwargs)
        runner = _runners.SyncTaskRunner(
            task_class,
            task_kwargs,
            controller,
            on_started=lambda: _emit_started(self_ref, holder),
        )

        raw_future: futures.Future[VariableContainer] = futures.Future()

        return self._finalize_submission(
            raw_future,
            controller,
            holder,
            self_ref,
            after_submitted=lambda: _sync_submit(runner, raw_future),
        )

    def _submit_thread(
        self, task_class: Type[Task], task_kwargs: Dict[str, Any]
    ) -> TaskFuture:
        controller = _controllers.ThreadTaskController()
        ready_event = Event()
        self_ref = weakref.ref(self)
        holder: List[Optional[TaskFuture]] = [None]
        task_kwargs = self._handle_progess_arg(task_class, task_kwargs)
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

    def _submit_process(
        self, task_class: Type[Task], task_kwargs: Dict[str, Any]
    ) -> TaskFuture:
        manager = self._get_manager()

        ready_event = manager.Event()
        started_queue = manager.Queue()
        progress_queue = manager.Queue()
        abort_event = manager.Event()
        aborted_event = manager.Event()

        controller = _controllers.ProcessTaskController(
            abort_event, aborted_event, started_queue, progress_queue
        )

        task_kwargs = self._handle_progess_arg(
            task_class, task_kwargs, controller, progress_queue
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

    def _handle_progess_arg(
        self,
        task_class: Type[Task],
        task_kwargs: Dict[str, Any],
        controller: Optional[_controllers.ProcessTaskController] = None,
        progress_queue: Optional[Queue] = None,
    ) -> Dict[str, Any]:
        """Prepare the `progress` task argument for `task_class`.

        Dropped outright if `task_class` does not support progress reporting.

        For a process backend, the caller's progress object is usually
        unpicklable (QObject), so it's replaced by a queue-backed
        stand-in relaying values back to it.

        :return: The task arguments to submit.
        """
        if "progress" not in task_kwargs:
            return task_kwargs

        task_kwargs = dict(task_kwargs)
        progress = task_kwargs.pop("progress")

        if progress is None or not issubclass(task_class, TaskWithProgress):
            return task_kwargs

        if controller is None or progress_queue is None:
            task_kwargs["progress"] = progress
            return task_kwargs

        task_kwargs["progress"] = _progress.QueueProgress(progress_queue)
        controller.watch_progress(lambda value: setattr(progress, "progress", value))
        return task_kwargs

    def _finalize_submission(
        self,
        raw_future: futures.Future[VariableContainer],
        controller: _controllers.TaskController,
        holder: List[Optional[TaskFuture]],
        self_ref: weakref.ReferenceType["EwoksExecutor"],
        after_submitted: Callable[[], None],
    ) -> TaskFuture:
        task_future = TaskFuture(raw_future, controller)

        holder[0] = task_future

        self.submitted.emit(task_future)

        after_submitted()

        raw_future.add_done_callback(
            lambda f: _done_callback(self_ref, f, task_future, controller)
        )

        return task_future

    def _get_manager(self) -> multiprocessing.managers.SyncManager:
        if self._manager is None:
            context = self._mp_context or multiprocessing
            self._manager = context.Manager()

        return self._manager

    def _handle_done(
        self,
        raw_future: futures.Future[VariableContainer],
        task_future: TaskFuture,
        controller: _controllers.TaskController,
    ) -> None:
        with self._lock:
            self._running -= 1

        # Before emitting anything: this delivers the progress values still in
        # flight, so receivers of "succeeded"/"failed" cannot observe progress
        # arriving after they considered the task finished.
        controller.stop_progress()

        if raw_future.cancelled():
            return

        # The task necessarily started before the raw future could finish, but
        # "started" and "finished" travel through independent channels for the
        # process backend, so wait for "started" to keep signal order sane.
        controller.wait_started(timeout=5.0)

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
        executor, self._executor = self._executor, None
        manager, self._manager = self._manager, None

        def _shutdown() -> None:
            if executor is not None:
                executor.shutdown(wait=True)
            if manager is not None:
                manager.shutdown()

        if wait:
            _shutdown()
            return

        # Wait off-thread rather than `executor.shutdown(wait=False)`: on
        # Python < 3.9, garbage-collecting a `ProcessPoolExecutor` mid-shutdown
        # can orphan a worker process, hanging the interpreter at exit.
        Thread(target=_shutdown, name="EwoksExecutorShutdown").start()


def _done_callback(
    executor_ref: weakref.ReferenceType[EwoksExecutor],
    raw_future: futures.Future[VariableContainer],
    task_future: TaskFuture,
    controller: _controllers.TaskController,
) -> None:
    executor = executor_ref()
    if executor is not None:
        executor._handle_done(raw_future, task_future, controller)


def _emit_started(
    executor_ref: weakref.ReferenceType[EwoksExecutor],
    holder: List[Optional[TaskFuture]],
) -> None:
    executor = executor_ref()
    if executor is not None and holder and holder[0] is not None:
        executor.started.emit(holder[0])


def _sync_submit(
    fn: Callable[[], VariableContainer],
    raw_future: futures.Future[VariableContainer],
) -> None:
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
