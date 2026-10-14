from abc import ABC
from abc import abstractmethod
from typing import Callable
from typing import Optional


class TaskController(ABC):
    """Interface for controlling a running ewoks task.

    The task (instance) is expected to be executed at most once.
    """

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

    def watch(
        self,
        on_about_to_start: Callable[[], None],
        on_started: Callable[[], None],
        on_progress: Optional[Callable[[float], None]] = None,
    ) -> None:
        """Register `on_about_to_start` and `on_started` to be called once the
        task is about to start and once it has started, and `on_progress` (if
        any) for every progress value the task reports.

        Optional: only meaningful for controllers where these events are
        reported through a channel separate from task completion.
        """
        raise NotImplementedError(f"{type(self).__name__} has no events watcher")

    def stop_watching(self) -> None:
        """Stop watching, after delivering every event received so far.

        No-op by default, since most controllers let the task report its
        events directly.
        """
