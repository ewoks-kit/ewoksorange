from __future__ import annotations

import logging
import multiprocessing
import multiprocessing.context
import multiprocessing.managers
import weakref
from concurrent import futures
from enum import Enum
from enum import auto
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
from AnyQt.QtCore import Qt
from AnyQt.QtCore import Signal
from ewokscore import TaskWithProgress
from ewokscore.task import Task
from ewokscore.variable import VariableContainer

from . import _controllers
from . import _messages
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
    if concurrency is Concurrency.THREAD:
        return futures.ThreadPoolExecutor(max_workers=max_workers)
    raise ValueError(f"Concurrency policy {concurrency} is not handled")


class EwoksExecutor(QObject):
    """Qt-aware executor for ewoks tasks.

    Wraps a `concurrent.futures.Executor` (thread, process or None) and emits Qt
    signals on task lifecycle events. Returns :class:`TaskFuture` objects to cancel
    or stop the task. Their result is the executed task's
    :class:`~ewokscore.variable.VariableContainer` of output variables.
    """

    submitted = Signal(TaskFuture)
    """Emitted when a task is submitted."""

    aboutToStart = Signal(TaskFuture)
    """Emitted when a worker picks the task up, right before it is created and
    executed. Not emitted for a task prevented from starting."""

    started = Signal(TaskFuture)
    """Emitted when a task starts executing."""

    succeeded = Signal(TaskFuture)
    """Emitted when a task finishes successfully."""

    failed = Signal(TaskFuture)
    """Emitted when a task raises an exception, also when a stop prevented its start."""

    ignored = Signal()
    """Emitted when a task submission is ignored due to the DROP_IF_BUSY policy."""

    cancelled = Signal(TaskFuture)
    """Emitted when :meth:`TaskFuture.cancel` prevented a queued task from starting."""

    stopRequested = Signal(TaskFuture)
    """Emitted when a task finishes after :meth:`TaskFuture.request_stop` prevented its start or reached it."""

    finished = Signal(TaskFuture)
    """Emitted last, for every submitted task."""

    _done = Signal(object, object, object)
    # Carries a done task to the thread of the executor, behind the events
    # already queued for that thread.

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

        self._done.connect(self._handle_done, Qt.ConnectionType.QueuedConnection)

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

        try:
            if self._executor is None:
                return self._submit_sync(task_class, task_kwargs)

            if self._as_process:
                return self._submit_process(task_class, task_kwargs)

            return self._submit_thread(task_class, task_kwargs)
        except BaseException:
            with self._lock:
                self._running -= 1
            raise

    def _submit_sync(
        self, task_class: Type[Task], task_kwargs: Dict[str, Any]
    ) -> TaskFuture:
        controller = _controllers.SyncTaskController()
        self_ref = weakref.ref(self)
        holder: List[Optional[TaskFuture]] = [None]
        task_kwargs = self._handle_progress_arg(task_class, task_kwargs)
        runner = _runners.SyncTaskRunner(
            task_class,
            task_kwargs,
            controller,
            on_about_to_start=lambda: _emit_about_to_start(self_ref, holder),
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
        task_kwargs = self._handle_progress_arg(task_class, task_kwargs)
        runner = _runners.ThreadTaskRunner(
            task_class,
            task_kwargs,
            controller,
            ready_event,
            on_about_to_start=lambda: _emit_about_to_start(self_ref, holder),
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

        to_controller_queue = manager.Queue()
        to_runner_queue = manager.Queue()

        controller = _controllers.ProcessTaskController(
            to_controller_queue, to_runner_queue
        )

        # The caller's progress object is usually unpicklable (QObject), so
        # it's replaced by a queue-backed stand-in relaying values back to it.
        progress = self._pop_progress_arg(task_class, task_kwargs)
        on_progress: Optional[Callable[[float], None]] = None
        if progress is not None:
            task_kwargs["progress"] = _messages.QueueProgress(to_controller_queue)

            def on_progress(value: float) -> None:
                progress.progress = value

        runner = _runners.ProcessTaskRunner(
            task_class, task_kwargs, to_controller_queue, to_runner_queue
        )

        self_ref = weakref.ref(self)
        holder: List[Optional[TaskFuture]] = [None]

        raw_future = self._executor.submit(runner)

        def watch() -> None:
            # Only after the submission (a failing 'submit' is never watched) and
            # after "submitted" (the runner cannot start before the relay allows it).
            controller.watch(
                on_about_to_start=lambda: _emit_about_to_start(self_ref, holder),
                on_started=lambda: _emit_started(self_ref, holder),
                on_progress=on_progress,
            )

        return self._finalize_submission(
            raw_future, controller, holder, self_ref, after_submitted=watch
        )

    def _handle_progress_arg(
        self, task_class: Type[Task], task_kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare the `progress` task argument for `task_class`, for backends
        where the task can update the caller's progress object directly.

        :return: The task arguments to submit.
        """
        progress = self._pop_progress_arg(task_class, task_kwargs)
        if progress is not None:
            task_kwargs["progress"] = progress
        return task_kwargs

    @staticmethod
    def _pop_progress_arg(task_class: Type[Task], task_kwargs: Dict[str, Any]) -> Any:
        """Remove the `progress` task argument from `task_kwargs`.

        :return: The progress object, or `None` if there is none or
            `task_class` does not support progress reporting (so it's dropped).
        """
        progress = task_kwargs.pop("progress", None)
        if progress is None or not issubclass(task_class, TaskWithProgress):
            return None
        return progress

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

        queue_done = self._executor is not None
        raw_future.add_done_callback(
            lambda f: _done_callback(self_ref, f, task_future, controller, queue_done)
        )

        return task_future

    def _get_manager(self) -> multiprocessing.managers.SyncManager:
        with self._lock:
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
        if task_future.cancelled():
            self.cancelled.emit(task_future)
            self.finished.emit(task_future)
            return

        if task_future.stop_requested():
            self.stopRequested.emit(task_future)

        if task_future.exception() is None:
            self.succeeded.emit(task_future)
        else:
            self.failed.emit(task_future)
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
    queue_done: bool,
) -> None:
    # Before emitting anything: this queues the events still in flight
    # (process backend) for the thread of the executor. Done even if the
    # executor is gone, so the relay never outlives the task.
    controller.stop_watching()

    executor = executor_ref()
    if executor is None:
        return

    with executor._lock:
        executor._running -= 1

    if queue_done:
        # The other signals of the task are queued for the thread of the
        # executor, also when this callback runs in that thread (a task that
        # finished before the callback was added). The completion signals must
        # not overtake them.
        executor._done.emit(raw_future, task_future, controller)
    else:
        executor._handle_done(raw_future, task_future, controller)


def _emit_about_to_start(
    executor_ref: weakref.ReferenceType[EwoksExecutor],
    holder: List[Optional[TaskFuture]],
) -> None:
    executor = executor_ref()
    if executor is not None and holder and holder[0] is not None:
        executor.aboutToStart.emit(holder[0])


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
