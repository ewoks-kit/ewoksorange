from abc import ABC
from abc import abstractmethod


class TaskController(ABC):
    """Interface for controlling a running ewoks task."""

    @abstractmethod
    def abort(self) -> bool:
        """Request task abortion.

        Returns True if the abort request reached the task.
        """
        raise NotImplementedError

    @abstractmethod
    def aborted(self) -> bool:
        """Return True if the task was actually aborted."""
        raise NotImplementedError
