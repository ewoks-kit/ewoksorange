import threading
from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import Optional
from typing import Type

from ewokscore.task import Task
from ewokscore.variable import VariableContainer

from .._controllers.abstract import StartDenial
from ..future import TaskAbortedError
from ..future import TaskStoppedError


class TaskRunner(ABC):
    """Base class for ewoks task execution runners."""

    def __init__(self, task_class: Type[Task], task_kwargs: Dict[str, Any]):
        self._task_class = task_class
        self._task_kwargs = task_kwargs

    def __call__(self) -> Optional[VariableContainer]:
        self._wait_ready()
        denial = self._try_start()
        if denial is StartDenial.CANCELLED:
            return None
        if denial is not None:
            raise _denial_error(self._task_class, denial)
        self._announce_about_to_start()
        task = self._create_task()
        self._announce_started(task)
        return self._execute(task)

    def _wait_ready(self) -> None:
        """Block until the task may be created and executed."""

    @abstractmethod
    def _try_start(self) -> Optional[StartDenial]:
        """Return why the task must not be executed, `None` to execute it."""
        raise NotImplementedError

    @abstractmethod
    def _announce_about_to_start(self) -> None:
        """Announce the task is about to be created and executed."""
        raise NotImplementedError

    @abstractmethod
    def _announce_started(self, task: Task) -> None:
        """Announce `task` as started."""
        raise NotImplementedError

    def _create_task(self) -> Task:
        """Instantiate task class."""
        return self._task_class(**self._task_kwargs)

    @abstractmethod
    def _execute(self, task: Task) -> VariableContainer:
        """Execute `task`, requesting it to stop when requested by the caller."""
        raise NotImplementedError

    def _execute_with_stop_event(
        self, task: Task, stop_event: threading.Event
    ) -> VariableContainer:
        """Execute `task`, requesting it to stop for as long as `stop_event` is set."""
        done = threading.Event()

        def _watch_stop_request():
            """
            `task.execute()` resets the task's `stop_requested` flag, which
            can silently undo a `request_stop()` racing with the start
            of execution.

            For this reason this watcher thread keeps re-applying `task.request_stop()`
            until execution finishes, so a task's `run()` reliably observes it
            regardless of the timing.

            The output of a task requested to stop is undefined. It could be an
            exception, undefined outputs, pertially defined outputs or
            fully defined outputs.
            """
            stop_event.wait()
            if done.is_set():
                # Woken up only to let this thread exit; the task
                # finished without ever being requested to stop.
                return
            while not done.is_set():
                task.request_stop()
                done.wait(timeout=0.01)

        watcher = threading.Thread(target=_watch_stop_request, daemon=True)
        watcher.start()
        try:
            self._execute_task(task)
        finally:
            done.set()
            # Wake the watcher if the task completed without stop request.
            stop_event.set()
            watcher.join()

        return task.output_variables

    def _execute_task(self, task: Task) -> None:
        task.execute(raise_on_error=True)


def _denial_error(task_class: Type[Task], denial: StartDenial) -> Exception:
    """The error of a task that was not allowed to start."""
    name = task_class.__name__
    if denial is StartDenial.STOPPED:
        return TaskStoppedError(f"Task {name} was stopped before it started")
    if denial is StartDenial.ABORTED:
        return TaskAbortedError(f"Task {name} was aborted before it started")
    if denial is StartDenial.KILLED:
        return TaskAbortedError(f"Task {name} was killed before it started")
    return ValueError(f"Start denial {denial} is not handled")
