import logging
import multiprocessing
import multiprocessing.managers
import threading
import weakref
from concurrent.futures import Executor
from concurrent.futures import Future
from concurrent.futures import ProcessPoolExecutor
from enum import Enum
from enum import auto
from threading import Event
from threading import Lock
from typing import Optional
from typing import Type

from AnyQt.QtCore import QObject
from AnyQt.QtCore import Signal
from ewokscore.task import Task

from ._EwoksProcessHandle import EwoksProcessHandle as _EwoksProcessHandle
from ._EwoksThreadHandle import EwoksThreadHandle as _EwoksThreadHandle
from ._ProcessCallable import ProcessCallable as _ProcessCallable
from .TaskFuture import TaskFuture

_logger = logging.getLogger(__name__)


class SubmitPolicy(Enum):
    ALWAYS = auto()
    DROP_IF_BUSY = auto()


class EwoksExecutor(QObject):
    """Qt-aware executor for ewoks tasks.

    Wraps a concurrent.futures.Executor (thread or process) and emits Qt
    signals on task lifecycle events.  Returns TaskFuture objects that support
    both native future cancellation (cancel()) and ewoks task abort (abort()).

    The `started` signal is always emitted in the main thread regardless of
    the executor type.

    Warning: the `ProcessPoolExecutor` implementation is a beta-version.
    """

    submitted = Signal(object)
    """Emitted when a task is submitted. Argument is the TaskFuture."""
    started = Signal(object)
    """Emitted when a task starts executing. Argument is the TaskFuture."""
    succeeded = Signal(object, object)
    """Emitted when a task finishes successfully. Arguments are the TaskFuture and the result dict."""
    failed = Signal(object, object)
    """Emitted when a task raises an exception. Arguments are the TaskFuture and the exception."""
    ignored = Signal()
    """Emitted when a task submission is ignored due to the DROP_IF_BUSY policy."""
    aborted = Signal(object)
    """Emitted when a task was aborted. Argument is the TaskFuture."""
    finished = Signal(object)
    """Emitted when a task finishes (success, failure, or abort). Argument is the TaskFuture."""

    def __init__(
        self,
        executor: Executor,
        policy: SubmitPolicy = SubmitPolicy.ALWAYS,
    ):
        super().__init__()
        self._executor = executor
        self._policy = policy
        self._running = 0
        self._lock = Lock()
        self._is_process = isinstance(executor, ProcessPoolExecutor)
        # Manager is started lazily on first process submission and provides
        # picklable proxy Queue / Event objects for IPC.
        self._manager: Optional[multiprocessing.managers.SyncManager] = None

    def submit_task(
        self,
        task_class: Type[Task],
        **task_kwargs,
    ) -> Optional[TaskFuture]:
        """Submit an ewoks task for execution.

        task_kwargs are forwarded directly to the task class constructor
        (e.g. ``inputs={"a": 1}``).  Returns a TaskFuture, or None if the
        policy dropped the submission.
        """
        with self._lock:
            if self._policy is SubmitPolicy.DROP_IF_BUSY and self._running:
                _logger.warning("Submission ignored: executor busy")
                self.ignored.emit()
                return None
            self._running += 1

        if self._is_process:
            return self._submit_process(task_class, task_kwargs)
        return self._submit_thread(task_class, task_kwargs)

    def _submit_thread(self, task_class, task_kwargs) -> TaskFuture:
        worker = _EwoksThreadHandle(task_class, **task_kwargs)
        self_ref = weakref.ref(self)

        # _ready gates the worker until task_future is assigned so that
        # `started` is never emitted with a None reference.
        _ready: Event = Event()
        _holder: list = [None]

        def _run():
            _ready.wait()
            self._emit_started(self_ref, _holder)
            return worker()

        raw_future = self._executor.submit(_run)
        return self._finalize_submission(
            raw_future, worker, self_ref, _holder, ready=_ready
        )

    def _submit_process(self, task_class, task_kwargs) -> TaskFuture:
        manager = self._get_manager()
        started_queue = manager.Queue()
        abort_event = manager.Event()
        aborted_event = manager.Event()

        callable_obj = _ProcessCallable(
            task_class, task_kwargs, started_queue, abort_event, aborted_event
        )
        worker = _EwoksProcessHandle(abort_event, aborted_event)
        self_ref = weakref.ref(self)
        _holder: list = [None]

        # A daemon thread blocks on the queue and relays "started" to the
        # Qt main thread once the subprocess signals it.
        def _relay_started():
            try:
                msg = started_queue.get(timeout=300)
                if msg == "started":
                    self._emit_started(self_ref, _holder)
            except Exception:
                _logger.debug("started relay timed out or failed", exc_info=True)

        threading.Thread(target=_relay_started, daemon=True).start()

        raw_future = self._executor.submit(callable_obj)
        return self._finalize_submission(raw_future, worker, self_ref, _holder)

    def _finalize_submission(
        self,
        raw_future: Future,
        worker,
        self_ref,
        holder: list,
        ready: Optional[Event] = None,
    ) -> TaskFuture:
        task_future = TaskFuture(raw_future, worker)
        # Store the TaskFuture in a mutable list so the _run() closure can see it after _ready is set.
        holder[0] = task_future
        if ready is not None:
            ready.set()

        # submitted fires before add_done_callback so it is always the first
        # signal — even when the task finishes so fast that add_done_callback
        # calls the callback synchronously in this thread.
        self.submitted.emit(task_future)
        raw_future.add_done_callback(
            lambda f: self._done_callback(self_ref, f, task_future)
        )
        return task_future

    def _get_manager(self):
        if self._manager is None:
            # SyncManager server process provides proxy objects that are
            # picklable and safe to pass through ProcessPoolExecutor's pickle
            # serialisation.  A plain multiprocessing.Queue is NOT picklable.
            self._manager = multiprocessing.Manager()
        return self._manager

    def _handle_done(self, raw_future: Future, task_future: TaskFuture) -> None:
        with self._lock:
            self._running -= 1

        if raw_future.cancelled():
            return

        if task_future.aborted():
            self.aborted.emit(task_future)

        try:
            result = raw_future.result()
        except Exception as exc:
            self.failed.emit(task_future, exc)
        else:
            self.succeeded.emit(task_future, result)
        finally:
            self.finished.emit(task_future)

    def shutdown(self, wait: bool = False) -> None:
        self._executor.shutdown(wait=wait)
        if self._manager is not None:
            self._manager.shutdown()
            self._manager = None

    @staticmethod
    def _done_callback(
        executor_ref, raw_future: Future, task_future: TaskFuture
    ) -> None:
        executor = executor_ref()
        if executor is None:
            return
        executor._handle_done(raw_future, task_future)

    @staticmethod
    def _emit_started(self_ref, holder: list) -> None:
        exe = self_ref()
        if exe is not None:
            exe.started.emit(holder[0])
