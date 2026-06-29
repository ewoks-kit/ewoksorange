import threading
from collections import namedtuple
from typing import Type

from ewokscore.task import Task

_Var = namedtuple("_Var", ["value"])


class ProcessCallable:
    """Top-level picklable callable submitted to ProcessPoolExecutor.

    IPC is handled by two objects passed at construction time:
    - started_queue: multiprocessing.Queue — worker puts "started" when running
    - abort_event:   multiprocessing.Event — main process sets to request cancel
    """

    def __init__(
        self,
        task_class: Type[Task],
        task_kwargs: dict,
        started_queue,
        abort_event,
    ):
        self._task_class = task_class
        self._task_kwargs = task_kwargs
        self._started_queue = started_queue
        self._abort_event = abort_event

    def __call__(self):
        task_class = self._task_class
        kwargs = dict(self._task_kwargs)
        task = task_class(**kwargs)

        # A daemon thread watches for the abort signal and calls task.cancel().
        # `done` prevents cancel() from being called after the task has already
        # finished naturally.
        done = threading.Event()

        def _watch_abort():
            self._abort_event.wait()
            if not done.is_set():
                task.cancel()

        watcher = threading.Thread(target=_watch_abort, daemon=True)
        watcher.start()

        # Signal "started" after the task and watcher are set up so that an
        # abort() arriving right after started cannot race with reset_state().
        self._started_queue.put("started")

        try:
            task.execute()
        finally:
            done.set()

        # Return a picklable representation: {name: _Var(value)}
        return {k: _Var(v.value) for k, v in task.output_variables.items()}
