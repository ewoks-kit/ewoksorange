import warnings
from typing import Optional

from AnyQt.QtCore import QThread

from .base import TaskExecutor


class ThreadedTaskExecutor(QThread, TaskExecutor):
    """Create and execute an Ewoks task in a dedicated thread."""

    def __init__(self, ewokstaskclass, parent=None):
        super().__init__(parent=parent, ewokstaskclass=ewokstaskclass)
        warnings.warn(
            f"ThreadedTaskExecutor is deprecated since version 6.0."
            "Please use 'ewoksorange.gui.concurrency.executor.EwoksExecutor' instead.",
            DeprecationWarning,
            stacklevel=2,
        )

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
