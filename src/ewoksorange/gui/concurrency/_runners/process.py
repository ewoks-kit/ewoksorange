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
from .._messages import ToController
from .._messages import ToRunner
from ..future import TaskAbortedError
from .abstract import TaskRunner

_EXECUTING = False


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
        return None if reply is ToRunner.START else reply

    def _announce_about_to_start(self) -> None:
        # The controller announces it when allowing the start.
        pass

    def _announce_started(self, task: Task) -> None:
        self._to_controller_queue.put(ToController.STARTED)

    def _execute(self, task: Task) -> VariableContainer:
        """Execute `task`, handling the stop and abort requests of the controller."""
        global _EXECUTING

        _install_sigint_handler()
        stop_event = threading.Event()
        abort_sent = threading.Event()

        def _read_to_runner_queue():
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

        reader = threading.Thread(target=_read_to_runner_queue, daemon=True)
        reader.start()
        try:
            return self._execute_with_stop_event(task, stop_event)
        except KeyboardInterrupt:
            if abort_sent.is_set():
                raise TaskAbortedError(
                    f"Task {type(task).__name__} was aborted"
                ) from None
            raise
        finally:
            _EXECUTING = False
            try:
                # Wake the reader.
                self._to_runner_queue.put(ToRunner.END)
            except self._TRANSIENT_ERRORS:
                pass
            reader.join()

    def _run_task(self, task: Task) -> None:
        global _EXECUTING

        # SIGINT only interrupts the task, not the runner.
        _EXECUTING = True
        try:
            super()._run_task(task)
        finally:
            _EXECUTING = False


_SIGINT_HANDLER_INSTALLED = False


def _install_sigint_handler() -> None:
    """Interrupt the task with `KeyboardInterrupt` on `SIGINT`.

    The handler stays installed so that `SIGINT` never kills an idle worker,
    which would break the process pool.
    """
    global _SIGINT_HANDLER_INSTALLED

    if _SIGINT_HANDLER_INSTALLED:
        return
    signal.signal(signal.SIGINT, _sigint_handler)
    _SIGINT_HANDLER_INSTALLED = True


def _sigint_handler(signum: int, frame: Any) -> None:
    if _EXECUTING:
        raise KeyboardInterrupt


def _interrupt_main_thread() -> None:
    if sys.platform == "win32":
        # Unlike a real signal, this does not interrupt blocking calls.
        _thread.interrupt_main()
    else:
        signal.pthread_kill(threading.main_thread().ident, signal.SIGINT)
