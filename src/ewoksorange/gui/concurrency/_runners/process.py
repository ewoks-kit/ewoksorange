import queue
import threading
from typing import Any
from typing import Dict
from typing import Type

from ewokscore.task import Task
from ewokscore.variable import VariableContainer

from .abstract import TaskRunner


class ProcessTaskRunner(TaskRunner):
    """Picklable callable executed inside the subprocess.

    Owns the task instance and communicates lifecycle information back to the
    parent process through multiprocessing primitives.
    """

    def __init__(
        self,
        task_class: Type[Task],
        task_kwargs: Dict[str, Any],
        ready_event: threading.Event,
        started_queue: queue.Queue,
        abort_event: threading.Event,
        aborted_event: threading.Event,
    ):
        super().__init__(task_class, task_kwargs)
        self._ready_event = ready_event
        self._started_queue = started_queue
        self._abort_event = abort_event
        self._aborted_event = aborted_event

    def __call__(self) -> VariableContainer:
        self._ready_event.wait()

        task = self._create_task()

        done = threading.Event()

        def _watch_abort():
            try:
                self._abort_event.wait()

                if done.is_set():
                    # The abort event was only used to wake this thread during
                    # normal shutdown.
                    return

                task.cancel()

                done.wait()
                self._aborted_event.set()

            except (EOFError, BrokenPipeError, ConnectionError):
                # The manager providing the IPC objects shut down.
                pass

        watcher = threading.Thread(target=_watch_abort, daemon=True)
        watcher.start()

        # Signal the parent only after both the task and abort watcher are
        # ready, so abort() cannot race with task creation.
        self._started_queue.put("started")

        try:
            return self._execute(task)
        finally:
            done.set()

            # Wake the watcher if the task completed normally.
            self._abort_event.set()

            watcher.join(timeout=5)
