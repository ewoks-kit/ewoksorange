import threading
from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import Tuple
from typing import Type

from ewokscore.task import Task
from ewokscore.variable import VariableContainer


class TaskRunner(ABC):
    """Base class for ewoks task execution runners."""

    _TRANSIENT_STOP_ERRORS: Tuple[Type[Exception], ...] = ()

    def __init__(
        self,
        task_class: Type[Task],
        task_kwargs: Dict[str, Any],
        stop_event: threading.Event,
    ):
        self._task_class = task_class
        self._task_kwargs = task_kwargs
        self._stop_event = stop_event

    def __call__(self) -> VariableContainer:
        self._wait_ready()
        self._announce_about_to_start()
        task = self._create_task()
        # Announce (only) once the task exists, so a request_stop() reacting to
        # that signal always finds a task to stop.
        self._announce_started(task)
        try:
            return self._execute(task)
        finally:
            self._finalize(task)

    def _wait_ready(self) -> None:
        """Block until the task may be created and executed."""

    @abstractmethod
    def _announce_about_to_start(self) -> None:
        """Announce the task is about to be created and executed."""
        raise NotImplementedError

    @abstractmethod
    def _announce_started(self, task: Task) -> None:
        """Register `task` (if applicable) and announce it as started."""
        raise NotImplementedError

    def _finalize(self, task: Task) -> None:
        """Called once execution has finished, however it ended."""

    def _create_task(self) -> Task:
        """Instantiate task class."""
        return self._task_class(**self._task_kwargs)

    def _execute(self, task: Task) -> VariableContainer:
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
            try:
                self._stop_event.wait()
                if done.is_set():
                    # Woken up only to let this thread exit; the task
                    # finished without ever being requested to stop.
                    return
                while not done.is_set():
                    task.request_stop()
                    done.wait(timeout=0.01)
            except self._TRANSIENT_STOP_ERRORS:
                pass

        watcher = threading.Thread(target=_watch_stop_request, daemon=True)
        watcher.start()
        try:
            task.execute(raise_on_error=True)
        finally:
            done.set()
            try:
                # Wake the watcher if the task completed without stop request.
                self._stop_event.set()
            except self._TRANSIENT_STOP_ERRORS:
                pass
            watcher.join()

        return task.output_variables
