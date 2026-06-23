from dataclasses import dataclass
from typing import Callable
from typing import Dict
from typing import Iterable
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
    task_executor: ThreadedTaskExecutor
    callbacks: Iterable[Callable[[ThreadedTaskExecutor], None]]
    started: bool = False


class MultiThreadedTaskExecutor(QObject):
    """Create and execute each Ewoks task in its own dedicated thread."""

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
        _callbacks: Iterable[Callable[[ThreadedTaskExecutor], None]] = tuple(),
        log_missing_inputs: bool = False,
        **kwargs,
    ) -> None:
        """Create the next task to be executed in a dedicated thread."""
        task_executor = ThreadedTaskExecutor(ewokstaskclass=self.__ewokstaskclass)
        task_executor.create_task(log_missing_inputs=log_missing_inputs, **kwargs)
        self.__add_task_executor(task_executor, _callbacks)

    def execute_task(self) -> None:
        """Execute the task created by :meth:`create_task`."""
        state = self.__get_pending_state()
        if state is None:
            return

        task_executor = state.task_executor
        state.started = True

        if task_executor.has_task:
            task_executor.finished.connect(self.__process_ended)
            self.sigComputationStarted.emit()
            task_executor.start()
        else:
            self.__process_ended_direct(task_executor)

    def __process_ended(self):
        self.__process_ended_direct(self.sender())

    def __process_ended_direct(self, task_executor: ThreadedTaskExecutor):
        state = self.__task_executors.get(id(task_executor))
        if state is None:
            return

        self.__last_output_variables = task_executor.output_variables
        self.__last_task_succeeded = task_executor.succeeded
        self.__last_task_done = task_executor.done
        self.__last_task_exception = task_executor.exception

        try:
            for callback in state.callbacks:
                callback(task_executor)
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

    def cancel_running_tasks(self, wait=True):
        """Request cancellation of all running tasks."""
        for state in list(self.__task_executors.values()):
            if not state.started:
                continue
            task_executor = state.task_executor
            task_executor.cancel_running_task()
            task_executor.stop(wait=wait)

    def __add_task_executor(
        self,
        task_executor: ThreadedTaskExecutor,
        callbacks: Iterable[Callable[[ThreadedTaskExecutor], None]],
    ) -> None:
        self.__task_executors[id(task_executor)] = _TaskExecutorState(
            task_executor=task_executor,
            callbacks=tuple(callbacks),
        )

    def __remove_task_executor(self, task_executor: ThreadedTaskExecutor) -> None:
        if task_executor is None:
            return
        if task_executor.receivers(task_executor.finished) > 0:
            task_executor.finished.disconnect(self.__process_ended)
        self.__task_executors.pop(id(task_executor), None)

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
