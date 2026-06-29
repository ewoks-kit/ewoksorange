"""
QtEwoksExecutor — Qt-aware concurrent.futures wrapper for ewoks tasks.

Usage::

    from concurrent.futures import ThreadPoolExecutor
    from ewoks_executor import QtEwoksExecutor, SubmitPolicy
    from mypackage.tasks import MyTask

    exe = QtEwoksExecutor(ThreadPoolExecutor(max_workers=2))
    tf = exe.submit_task(MyTask, inputs={"x": 1})

    # Prevent execution if the task has not started yet (native future cancel):
    tf.cancel()

    # Abort a running task by calling MyTask.cancel():
    tf.abort()
"""

import logging
from concurrent.futures import Executor
from concurrent.futures import Future
from enum import Enum
from enum import auto
from threading import Event
from threading import Lock
from typing import Optional
from typing import Type

from AnyQt.QtCore import QObject
from AnyQt.QtCore import Signal
from ewokscore import TaskWithProgress
from ewokscore.task import Task

_logger = logging.getLogger(__name__)


class SubmitPolicy(Enum):
    ALWAYS = auto()
    DROP_IF_BUSY = auto()


class _EwoksWorker:
    """Callable that instantiates and executes an ewoks task in the worker thread."""

    def __init__(self, task_class: Type[Task], **task_kwargs):
        self._task_class = task_class
        self._task_kwargs = task_kwargs
        self._task: Optional[Task] = None
        self._lock = Lock()

    def __call__(self):
        task_class = self._task_class
        kwargs = dict(self._task_kwargs)
        if not issubclass(task_class, TaskWithProgress):
            kwargs.pop("progress", None)

        task = task_class(**kwargs)
        with self._lock:
            self._task = task

        task.execute()
        return task.output_variables

    def abort(self) -> None:
        """Call the ewoks task's cancel() to stop a running task."""
        with self._lock:
            task = self._task
            if task is not None:
                task.cancel()

    @property
    def has_task(self) -> bool:
        with self._lock:
            return self._task is not None


class TaskFuture:
    """Wraps a concurrent.futures.Future with ewoks-specific abort support."""

    def __init__(self, raw_future: Future, worker: _EwoksWorker):
        self._future = raw_future
        self._worker = worker

    def cancel(self) -> bool:
        """Prevent execution if the task has not started (native future cancel)."""
        return self._future.cancel()

    def abort(self) -> None:
        """Abort a running ewoks task by calling its cancel() method."""
        self._worker.abort()

    def cancelled(self) -> bool:
        return self._future.cancelled()

    def running(self) -> bool:
        return self._future.running()

    def done(self) -> bool:
        return self._future.done()

    def result(self, timeout=None):
        return self._future.result(timeout=timeout)

    def exception(self, timeout=None):
        return self._future.exception(timeout=timeout)

    def add_done_callback(self, fn):
        self._future.add_done_callback(fn)


class EwoksExecutor(QObject):
    """Qt-aware executor for ewoks tasks.

    Wraps any concurrent.futures.Executor and emits Qt signals on task
    lifecycle events.
    """

    submitted = Signal(object)
    started = Signal(object)
    succeeded = Signal(object, object)
    failed = Signal(object, object)
    ignored = Signal()

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

    def submit_task(
        self,
        task_class: Type[Task],
        **task_kwargs,
    ) -> Optional[TaskFuture]:
        """Submit an ewoks task for execution."""
        with self._lock:
            if self._policy is SubmitPolicy.DROP_IF_BUSY and self._running:
                _logger.warning("Submission ignored: executor busy")
                self.ignored.emit()
                return None
            self._running += 1

        worker = _EwoksWorker(task_class, **task_kwargs)

        # _ready gates the worker until task_future exists, so that `started`
        # is always emitted with the correct TaskFuture reference and never
        # with None (which would happen if the worker thread reads _holder
        # before the main thread writes to it).
        _ready: Event = Event()
        _holder: list = [None]

        def _run():
            _ready.wait()
            self.started.emit(_holder[0])
            return worker()

        raw_future = self._executor.submit(_run)
        task_future = TaskFuture(raw_future, worker)
        _holder[0] = task_future
        _ready.set()

        self.submitted.emit(task_future)
        raw_future.add_done_callback(lambda f: self._on_done(f, task_future))
        return task_future

    def _on_done(self, raw_future: Future, task_future: TaskFuture) -> None:
        with self._lock:
            self._running -= 1

        if raw_future.cancelled():
            return

        try:
            result = raw_future.result()
        except Exception as exc:
            self.failed.emit(task_future, exc)
        else:
            self.succeeded.emit(task_future, result)

    def shutdown(self, wait: bool = False) -> None:
        self._executor.shutdown(wait=wait)
