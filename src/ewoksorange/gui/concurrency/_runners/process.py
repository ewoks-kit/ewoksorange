import queue
import threading
from typing import Any
from typing import Dict
from typing import Optional
from typing import Type

from ewokscore.task import Task
from ewokscore.variable import VariableContainer

from .._controllers.abstract import StartDenial
from .._messages import ToController
from .._messages import ToRunner
from .abstract import TaskRunner


class ProcessTaskRunner(TaskRunner):
    """Picklable callable executed inside the subprocess."""

    _TRANSIENT_ERRORS = (EOFError, BrokenPipeError, ConnectionError)
    # The manager providing the IPC objects shut down.

    def __init__(
        self,
        task_class: Type[Task],
        task_kwargs: Dict[str, Any],
        to_controller_queue: queue.Queue,
        to_runner_queue: queue.Queue,
    ):
        super().__init__(task_class, task_kwargs)
        self._to_controller_queue = to_controller_queue
        self._to_runner_queue = to_runner_queue

    def _try_start(self) -> Optional[StartDenial]:
        # The controller decides, so that a denied task never starts.
        self._to_controller_queue.put(ToController.ABOUT_TO_START)
        reply = self._to_runner_queue.get()
        if reply is ToRunner.START:
            return None
        if isinstance(reply, StartDenial):
            return reply
        raise RuntimeError(f"Unexpected start decision {reply!r}")

    def _announce_about_to_start(self) -> None:
        # The controller announces it when allowing the start.
        pass

    def _announce_started(self, task: Task) -> None:
        self._to_controller_queue.put(ToController.STARTED)

    def _execute(self, task: Task) -> VariableContainer:
        """Execute `task`, handling the stop requests of the controller."""
        stop_event = threading.Event()
        reader = threading.Thread(
            target=self._relay_stop_requests, args=(stop_event,), daemon=True
        )
        reader.start()
        try:
            return self._execute_with_stop_event(task, stop_event)
        finally:
            try:
                # Wake the reader.
                self._to_runner_queue.put(ToRunner.END)
            except self._TRANSIENT_ERRORS:
                pass
            reader.join()

    def _relay_stop_requests(self, stop_event: threading.Event) -> None:
        """Set `stop_event` on stop requests until `ToRunner.END` or the manager shuts down."""
        try:
            while True:
                message = self._to_runner_queue.get()
                if message is ToRunner.REQUEST_STOP:
                    stop_event.set()
                elif message is ToRunner.END:
                    return
        except self._TRANSIENT_ERRORS:
            pass
