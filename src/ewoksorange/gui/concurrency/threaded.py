import concurrent.futures
import uuid
import logging
from dataclasses import dataclass
from typing import Callable
from typing import Dict
from typing import Iterable
from typing import Optional

from AnyQt.QtCore import QObject
from AnyQt.QtCore import QThread
from AnyQt.QtCore import pyqtSignal as Signal

from ..concurrency._Executor import AbortableExecutor, CancellableExecutor
from ..concurrency._future import TaskFuture
from ..qt_utils.signals import block_signals
from .base import TaskExecutor

_logger = logging.getLogger(__name__)


class ThreadedTaskExecutor(QThread, TaskExecutor):
    """Create and execute an Ewoks task in a dedicated thread."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__current_future = None

    def create_task(self, log_missing_inputs=False, **kwargs):
        future = self._build_future()

        if self.isRunning():
            err = "A processing is already ongoing"
            future.set_exception(RuntimeError(err))
            _logger.error(err)
            return future
        super().create_task(log_missing_inputs, **kwargs)
        return future

    def _build_future(self):
        self.__current_future = super()._build_future()
        return self.__current_future

    def stop(self, timeout: Optional[float] = None, wait: bool = False) -> None:
        """Stop the current thread"""
        with block_signals(self):
            if wait:
                if timeout:
                    self.wait(timeout * 1000)
                else:
                    self.wait()
            if self.isRunning():
                self.quit()

    def _cancel_future(self, future: TaskFuture) -> bool:
        raise NotImplementedError("Cannot cancel a task")

    def _abort_future(self, future: TaskFuture) -> bool:
        # TODO: this class must store the future or the task_exec_id in order to be able to cancel it
        if (
            self.__current_future
            and future.task_exec_id == self.__current_future.task_exec_id
        ):
            self.current_task.cancel()
            return True
        return False


@dataclass
class _TaskExecutorState:
    task_executor: ThreadedTaskExecutor
    future: TaskFuture
    callbacks: Iterable[Callable[[ThreadedTaskExecutor, TaskFuture], None]]
    started: bool = False


class MultiThreadedTaskExecutor(QObject, CancellableExecutor, AbortableExecutor):
    """
    Execute each submitted Ewoks task in its own thread.

    Contrary to :class:`ThreadedTaskExecutor`, this executor owns the mapping
    between futures and per-run threads. This makes abort/cleanup independent
    from the widget using it.
    """

    sigComputationStarted = Signal()
    """Signal emitted when a computation is started"""

    sigComputationEnded = Signal()
    """Signal emitted when a computation is ended"""

    def __init__(self, ewokstaskclass):
        super().__init__()
        self.__ewokstaskclass = ewokstaskclass
        self.__task_executors: Dict[int, _TaskExecutorState] = dict()
        self.__last_output_variables = dict()
        self.__last_task_succeeded = None
        self.__last_task_done = None
        self.__last_task_exception = None

    def create_task(
        self,
        _callbacks: Iterable[
            Callable[[ThreadedTaskExecutor, TaskFuture], None]
        ] = tuple(),
        log_missing_inputs: bool = False,
        **kwargs,
    ) -> None:
        """Create the next task to be executed in a dedicated thread."""
        future = TaskFuture(task_exec_id=str(uuid.uuid4()), executor=self)
        future.task_kwargs = kwargs

        task_executor = ThreadedTaskExecutor(ewokstaskclass=self.__ewokstaskclass)
        task_executor.create_task(log_missing_inputs=log_missing_inputs, **kwargs)

        self.__add_task_executor(task_executor, future, _callbacks)

    def execute_task(self) -> TaskFuture:
        """Execute the task created by :meth:`create_task`."""
        state = self.__get_pending_state()
        if state is None:
            future = TaskFuture(task_exec_id=str(uuid.uuid4()), executor=self)
            future.set_exception(RuntimeError("Task not defined."))
            return future

        task_executor = state.task_executor
        future = state.future
        state.started = True
        task_executor.finished.connect(self.__process_ended)

        if task_executor.has_task:
            self.sigComputationStarted.emit()
            task_executor.start()
        else:
            task_executor.finished.emit()
        return future

    def __process_ended(self):
        self.__process_ended_direct(self.sender())

    def __process_ended_direct(self, task_executor: ThreadedTaskExecutor):
        state = self.__task_executors.get(id(task_executor))
        if state is None:
            return

        future = state.future
        self.__last_output_variables = task_executor.output_variables
        self.__last_task_succeeded = task_executor.succeeded
        self.__last_task_done = task_executor.done
        self.__last_task_exception = task_executor.exception

        if not future.done():
            exception = task_executor.exception
            if exception is not None:
                future.set_exception(exception)
            elif task_executor.current_task is None:
                future.set_exception(RuntimeError("Task not defined."))
            else:
                future.set_result(task_executor.current_task.get_output_values())

        try:
            for callback in state.callbacks:
                callback(task_executor, future)
            self.sigComputationEnded.emit()
        finally:
            self.__remove_task_executor(task_executor)

    def stop(self, timeout: Optional[float] = None, wait: bool = False) -> None:
        """Stop all tracked task threads."""
        for state in list(self.__task_executors.values()):
            task_executor = state.task_executor
            if task_executor.receivers(task_executor.finished) > 0:
                task_executor.finished.disconnect(self.__process_ended)
            task_executor.stop(timeout=timeout, wait=wait)
        self.__task_executors.clear()

    def __add_task_executor(
        self,
        task_executor: ThreadedTaskExecutor,
        future: TaskFuture,
        callbacks: Iterable[Callable[[ThreadedTaskExecutor, TaskFuture], None]],
    ) -> None:
        self.__task_executors[id(task_executor)] = _TaskExecutorState(
            task_executor=task_executor,
            future=future,
            callbacks=tuple(callbacks),
        )

    def __remove_task_executor(self, task_executor: ThreadedTaskExecutor) -> None:
        if task_executor is None:
            return
        if task_executor.receivers(task_executor.finished) > 0:
            task_executor.finished.disconnect(self.__process_ended)
        self.__task_executors.pop(id(task_executor), None)

    def __get_task_executor(
        self, future: TaskFuture
    ) -> Optional[ThreadedTaskExecutor]:
        for state in self.__task_executors.values():
            if state.future is future:
                return state.task_executor
        return None

    def __get_pending_state(self) -> Optional[_TaskExecutorState]:
        for state in self.__task_executors.values():
            if not state.started:
                return state
        return None

    @property
    def task_succeeded(self) -> Optional[bool]:
        return self.__last_task_succeeded

    @property
    def task_done(self) -> Optional[bool]:
        return self.__last_task_done

    @property
    def task_exception(self) -> Optional[Exception]:
        return self.__last_task_exception

    @property
    def output_variables(self) -> dict:
        return self.__last_output_variables

    def _cancel_future(self, future: TaskFuture) -> bool:
        return False

    def _abort_future(self, future: TaskFuture) -> bool:
        task_executor = self.__get_task_executor(future)
        if task_executor is None or task_executor.current_task is None:
            return False

        task_executor.current_task.cancel()
        if not future.done():
            future.set_exception(concurrent.futures.CancelledError())
        return True
