from dataclasses import dataclass
from typing import Callable
from typing import Iterable
from typing import List
from typing import Optional

from AnyQt.QtCore import QObject
from AnyQt.QtCore import QThread
from AnyQt.QtCore import pyqtSignal as Signal

from .base import TaskExecutor


class ThreadedTaskExecutor(QThread, TaskExecutor):
    """Create and execute an Ewoks task in a dedicated thread."""

    def run(self) -> None:
        self.execute_task()

    def stop(self, timeout: Optional[float] = None, wait: bool = False) -> None:
        """Stop the current thread"""
        self.blockSignals(True)
        if wait:
            if timeout:
                self.wait(timeout * 1000)
            else:
                self.wait()
        if self.isRunning():
            self.quit()

    def cancel_running_task(self):
        """
        cancel current processing.
        The targetted EwoksTask must have implemented the 'cancel' function
        """
        if self.current_task is not None:
            self.current_task.cancel()


@dataclass
class _TaskExecutorState:
    callbacks: Iterable[Callable[[ThreadedTaskExecutor], None]]
    task_kwargs: Dict[str, Any]
    log_missing_inputs: bool = False
    task_executor: Optional[ThreadedTaskExecutor] = None


class MultiThreadedTaskExecutor(QObject):
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
            self.__process_ended_direct(task_executor)

        return task_executor

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
