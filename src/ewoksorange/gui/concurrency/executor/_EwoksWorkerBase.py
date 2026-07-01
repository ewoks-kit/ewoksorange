from abc import ABC
from abc import abstractmethod


class EwoksWorkerBase(ABC):
    """Common interface for objects that control a running ewoks task.

    Instances are handed to `TaskFuture` so it can abort the underlying
    ewoks task regardless of whether it runs in a thread or a subprocess.
    """

    @abstractmethod
    def abort(self) -> None:
        """Abort the running ewoks task."""

    @property
    @abstractmethod
    def has_task(self) -> bool:
        """Whether a task has been assigned to this worker."""
