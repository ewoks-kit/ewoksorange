import concurrent.futures
import uuid
import logging
from dataclasses import dataclass
from typing import Callable
from typing import Iterable
from typing import List
from typing import Optional

from AnyQt.QtCore import QObject
from AnyQt.QtCore import QThread
from AnyQt.QtCore import pyqtSignal as Signal

from .base import TaskExecutor
from ..concurrency._Executor import AbortableExecutor, CancellableExecutor
from ..concurrency._future import TaskFuture
from ..qt_utils.signals import block_signals

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

    def run(self) -> None:
        self.execute_task()

    def _build_future(self) -> TaskFuture:
        # Used to store the current future before it is finished
        # and optionnally abort it.
        if self.__current_future is None:
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

    def _cancel_running_task(self) -> None:
        if self.current_task is not None:
            self.current_task.cancel()

    def _abort_future(self, future: TaskFuture) -> bool:
        # TODO: this class must store the future or the task_exec_id in order to be able to cancel it
        if (
            self.__current_future
            and future.task_exec_id == self.__current_future.task_exec_id
            and self.current_task is not None
        ):
            self.current_task.cancel()
            if not future.done():
                future.set_exception(concurrent.futures.CancelledError())
            return True
        return False

    @property
    def current_future(self) -> Optional[TaskFuture]:
        return self.__current_future


@dataclass
class _TaskExecutorState:
    callbacks: Iterable[Callable[[ThreadedTaskExecutor], None]]
    task_kwargs: dict
    log_missing_inputs: bool = False
    task_executor: Optional[ThreadedTaskExecutor] = None


class MultiThreadedTaskExecutor(QObject, CancellableExecutor, AbortableExecutor):
    """Create and execute each Ewoks task in its own dedicated thread."""

    sigComputationStarted = Signal()
    """Signal emitted when a computation is started"""

    sigComputationEnded = Signal()
    """Signal emitted when a computation is ended"""

    def __init__(self, ewokstaskclass):
        super().__init__()
        self.__ewokstaskclass = ewokstaskclass
        self.__task_executors: List[_TaskExecutorState] = []
        self.__last_output_variables = dict()
        self.__last_task_succeeded = None
        self.__last_task_done = None
        self.__last_task_exception = None

    def execute_task(
        self,
        _callbacks: Iterable[Callable[[ThreadedTaskExecutor], None]] = tuple(),
        log_missing_inputs: bool = False,
        **kwargs,
    ) -> Optional[ThreadedTaskExecutor]:
        """Execute a prepared task, or directly create and execute a new one."""
        task_executor = ThreadedTaskExecutor(ewokstaskclass=self.__ewokstaskclass)
        task_executor.create_task(
            log_missing_inputs=log_missing_inputs,
            **kwargs,
        )

        state = _TaskExecutorState(
            callbacks=tuple(_callbacks),
            task_kwargs=kwargs,
            log_missing_inputs=log_missing_inputs,
            task_executor=task_executor,
        )
        self.__add_task_executor(state)

        if task_executor.has_task:
            task_executor.finished.connect(self.__process_ended)
            self.sigComputationStarted.emit()
            task_executor.start()
        else:
            task_executor.execute_task()
            self.__process_ended_direct(task_executor)
        return task_executor.current_future

    def __process_ended(self):
        self.__process_ended_direct(self.sender())

    def _getState(self, task_executor: ThreadedTaskExecutor) -> _TaskExecutorState:
        return next(
            (
                state
                for state in self.__task_executors
                if state.task_executor is task_executor
            ),
            None,
        )

    def __process_ended_direct(self, task_executor: ThreadedTaskExecutor):
        state = self._getState(task_executor=task_executor)
        if state is None:
            return

        self.__last_output_variables = task_executor.output_variables
        self.__last_task_succeeded = task_executor.succeeded
        self.__last_task_done = task_executor.done
        self.__last_task_exception = task_executor.exception

        try:
            for callback in state.callbacks:
                callback(task_executor)
        finally:
            self.sigComputationEnded.emit()
            self.__remove_task_executor(task_executor)

    def stop(self, timeout: Optional[float] = None, wait: bool = False) -> None:
        """Stop all tracked task threads."""
        for state in list(self.__task_executors):
            task_executor = state.task_executor
            if task_executor is None:
                continue
            if task_executor.receivers(task_executor.finished) > 0:
                task_executor.finished.disconnect(self.__process_ended)
            task_executor.stop(timeout=timeout, wait=wait)
        self.__task_executors.clear()

    def cancel_running_tasks(self, wait=True):
        """Request cancellation of all running tasks."""
        for state in list(self.__task_executors):
            if state.task_executor is None or not state.task_executor.isRunning():
                continue
            task_executor = state.task_executor
            task_executor.cancel_running_task()
            task_executor.stop(wait=wait)

    def __add_task_executor(self, state: _TaskExecutorState) -> None:
        self.__task_executors.append(state)

    def __remove_task_executor(self, task_executor: ThreadedTaskExecutor) -> None:
        if task_executor is None:
            return
        for state in list(self.__task_executors):
            if state.task_executor is task_executor:
                if task_executor.receivers(task_executor.finished) > 0:
                    task_executor.finished.disconnect(self.__process_ended)
                self.__task_executors.remove(state)
                break

    def __get_task_executor(self, future: TaskFuture) -> Optional[ThreadedTaskExecutor]:
        return next(
            (
                state
                for state in self.__task_executors
                if state.current_future is future
            ),
            None,
        )

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
