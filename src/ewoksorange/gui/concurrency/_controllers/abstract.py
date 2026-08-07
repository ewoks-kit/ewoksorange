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

    def watch_started(self, on_started: Callable[[], None]) -> None:
        """Register `on_started` to be called once the task has started.

        Optional: only meaningful for controllers where "started" is reported
        through a channel separate from task completion.
        """
        raise NotImplementedError(f"{type(self).__name__} has no started watcher")

    def wait_started(self, timeout: Optional[float] = None) -> None:
        """Block until a pending `on_started` call (registered via
        `watch_started`) has been handled.

        No-op by default, since most controllers report "started" and
        completion through the same channel, in order.
        """

    def watch_progress(self, on_progress: Callable[[int], None]) -> None:
        """Register `on_progress` to be called for every progress value the
        task reports.

        Optional: only meaningful for controllers where the task cannot update
        the caller's progress object directly.
        """
        raise NotImplementedError(f"{type(self).__name__} has no progress watcher")

    def stop_progress(self) -> None:
        """Stop watching progress, after delivering everything received so far.

        No-op by default, since most controllers let the task update the
        caller's progress object directly.
        """
