import threading
from typing import Type

from ewokscore.task import Task


class ProcessCallable:
    """Top-level picklable callable submitted to ProcessPoolExecutor.

    IPC is handled by three objects passed at construction time:
    - started_queue: multiprocessing.Queue — worker puts "started" when running
    - abort_event:   multiprocessing.Event — main process sets to request cancel
    - aborted_event: multiprocessing.Event — worker sets once the task has
                     actually stopped running as a result of that request
    """

    def __init__(
        self,
        task_class: Type[Task],
        task_kwargs: dict,
        started_queue,
        abort_event,
        aborted_event,
    ):
        self._task_class = task_class
        self._task_kwargs = task_kwargs
        self._started_queue = started_queue
        self._abort_event = abort_event
        self._aborted_event = aborted_event

    def __call__(self):
        task_class = self._task_class
        kwargs = dict(self._task_kwargs)
        task = task_class(**kwargs)

        # A daemon thread watches for the abort signal and calls task.cancel().
        # `done` prevents cancel() from being called after the task has already
        # finished naturally. Once the task actually stops (execute() returns),
        # aborted_event is set so the main process can wait for abort completion.
        done = threading.Event()

        def _watch_abort():
            try:
                self._abort_event.wait()
                if done.is_set():
                    # abort_event was only set to release this thread.
                    return
                task.cancel()
                done.wait()
                self._aborted_event.set()
            except (EOFError, BrokenPipeError, ConnectionError):
                # The manager providing the event proxies shut down.
                pass

        watcher = threading.Thread(target=_watch_abort, daemon=True)
        watcher.start()

        # Signal "started" after the task and watcher are set up so that an
        # abort() arriving right after started cannot race with reset_state().
        self._started_queue.put("started")

        task_exc = None
        try:
            task.execute()
        except Exception as e:
            task_exc = e
        finally:
            done.set()
            # '_watch_abort' is waiting over the '_abort_event'. Release it.
            # If done is already set will just release the thread.
            self._abort_event.set()
            watcher.join(timeout=5)

        if task_exc is not None:
            raise task_exc
        return task.output_variables
