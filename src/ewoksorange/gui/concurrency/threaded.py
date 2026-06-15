from typing import Optional

from AnyQt.QtCore import QThread

from ..concurrency._future import TaskFuture
from ..qt_utils.signals import block_signals
from .base import TaskExecutor


class ThreadedTaskExecutor(QThread, TaskExecutor):
    """Create and execute an Ewoks task in a dedicated thread."""

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
