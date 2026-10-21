import _thread
import queue
import signal
import sys
import threading
from typing import Any
from typing import Dict
from typing import Optional
from typing import Type

from ewokscore.task import Task
from ewokscore.variable import VariableContainer

from .._controllers.abstract import StartDenial
from .._messages import QueueProgress
from .._messages import ToController
from .._messages import ToRunner
from ..future import TaskAbortedError
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
        self._abort_sent: Optional[threading.Event] = None

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
        """Execute `task`, handling the stop and abort requests of the controller."""
        stop_event = threading.Event()
        abort_sent = self._abort_sent = threading.Event()
        progress = self._task_kwargs.get("progress")
        if not isinstance(progress, QueueProgress):
            progress = None
        if progress is not None:
            progress.start_sending()
        reader = threading.Thread(
            target=self._relay_requests, args=(stop_event, abort_sent), daemon=True
        )
        reader.start()
        aborted = False
        try:
            return self._execute_with_stop_event(task, stop_event)
        except KeyboardInterrupt:
            if abort_sent.is_set():
                aborted = True
                raise TaskAbortedError(
                    f"Task {type(task).__name__} was aborted"
                ) from None
            raise
        finally:
            if progress is not None:
                # Before returning: the controller expects all progress values first.
                # Those of an aborted task do not matter.
                progress.stop_sending(discard=aborted)
            try:
                # Wake the reader.
                self._to_runner_queue.put(ToRunner.END)
            except self._TRANSIENT_ERRORS:
                pass
            reader.join()

    def _relay_requests(
        self, stop_event: threading.Event, abort_sent: threading.Event
    ) -> None:
        """Handle stop and abort requests until `ToRunner.END` or the manager shuts down."""
        try:
            while True:
                message = self._to_runner_queue.get()
                if message is ToRunner.REQUEST_STOP:
                    stop_event.set()
                elif message is ToRunner.ABORT:
                    if not abort_sent.is_set():
                        abort_sent.set()
                        _interrupt_main_thread()
                elif message is ToRunner.END:
                    return
        except self._TRANSIENT_ERRORS:
            pass

    def _run_task(self, task: Task) -> None:
        # SIGINT only interrupts the task, not the runner. Outside the task, the
        # pebble worker ignores SIGINT.
        previous = signal.signal(signal.SIGINT, _raise_keyboard_interrupt)
        try:
            try:
                if self._abort_sent is not None and self._abort_sent.is_set():
                    # The SIGINT arrived before the handler was installed and was ignored.
                    raise KeyboardInterrupt
                super()._run_task(task)
            finally:
                signal.signal(signal.SIGINT, previous)
        except KeyboardInterrupt:
            # The SIGINT can also interrupt the restore above.
            signal.signal(signal.SIGINT, previous)
            raise


def _raise_keyboard_interrupt(signum: int, frame: Any) -> None:
    """Interrupt the task like Ctrl-C."""
    raise KeyboardInterrupt


def _interrupt_main_thread() -> None:
    if sys.platform == "win32":
        # Unlike a real signal, this does not interrupt blocking calls.
        _thread.interrupt_main()
    else:
        signal.pthread_kill(threading.main_thread().ident, signal.SIGINT)
