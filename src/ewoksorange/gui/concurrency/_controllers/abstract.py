from abc import ABC
from abc import abstractmethod
from concurrent.futures import Future
from enum import Enum
from enum import auto
from threading import Lock
from typing import Callable
from typing import Optional


class StartDenial(Enum):
    """Why a task is not allowed to start."""

    CANCELLED = auto()
    STOPPED = auto()


class StartGate:
    """Decides once whether a task may start.

    The side executing the task calls `open` right before creating it, the side
    controlling it calls `deny`. Whichever takes the lock first decides.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._started = False
        self._denial: Optional[StartDenial] = None

    @property
    def started(self) -> bool:
        return self._started

    @property
    def denial(self) -> Optional[StartDenial]:
        return self._denial

    def deny(self, denial: StartDenial) -> bool:
        """Prevent the task from starting. Called by the side controlling the task.

        Returns False when the task already started or was denied before.
        """
        with self._lock:
            if self._started or self._denial is not None:
                return False
            self._denial = denial
            return True

    def open(self) -> Optional[StartDenial]:
        """Let the task start unless it was denied. Called by the side executing
        the task, right before creating it.

        Returns the denial, or `None` when the task may start.
        """
        with self._lock:
            self._started = self._denial is None
            return self._denial


class TaskController(ABC):
    """Interface for controlling an ewoks task.

    The task (instance) is expected to be executed at most once. Only the first
    of cancel and stop that reaches a task before it starts has an effect: the
    task never starts.
    """

    def __init__(self) -> None:
        self._gate = StartGate()
        self._stop_sent = False

    def request_stop(self) -> bool:
        """Request the task to stop, or prevent it from starting.

        Returns True if the stop request prevented the start or reached the task.
        """
        if self._gate.deny(StartDenial.STOPPED):
            return True
        if not self._gate.started:
            # Denied before, e.g. cancelled.
            return False
        self._stop_sent = True
        self._send_stop_request()
        return True

    @abstractmethod
    def _send_stop_request(self) -> None:
        """Request the running task to stop."""
        raise NotImplementedError

    def stop_requested(self) -> bool:
        """Return True if the stop request prevented the start or reached the task."""
        # Stopped before starting: the gate holds the denial, nothing was sent.
        # Stopped while running: the stop request was sent to the task.
        return self._gate.denial is StartDenial.STOPPED or self._stop_sent

    def cancel(self, future: Future) -> bool:
        """Prevent execution if the task has not started.

        Returns True if the task will not be executed.
        """
        return not future.done() and self._gate.deny(StartDenial.CANCELLED)

    def cancelled(self, future: Future) -> bool:
        """Return True if the task was cancelled before it started."""
        return self._gate.denial is StartDenial.CANCELLED

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
