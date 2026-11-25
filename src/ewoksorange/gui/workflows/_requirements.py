import importlib.metadata
import threading
from concurrent.futures import Future
from typing import Dict
from typing import Optional

from ewokscore import requirements

_lock = threading.Lock()
_last_thread: Optional[threading.Thread] = None


def generate_requirements_in_background() -> "Future[dict]":
    """Generate the requirements of the current Python environment in a daemon
    thread."""
    global _last_thread
    future = Future()
    with _lock:
        thread = threading.Thread(
            target=_generate,
            args=(future, _last_thread),
            name="ewoks-requirements",
            daemon=True,
        )
        _last_thread = thread
        thread.start()
    return future


def _generate(future: Future, previous: Optional[threading.Thread]) -> None:
    # One generation at a time: it reuses the result that ewokscore cached
    # for the previous one.
    if previous is not None:
        previous.join()
    if not future.set_running_or_notify_cancel():
        return
    try:
        result = requirements.generate_requirements(bootstrap=_bootstrap())
    except BaseException as ex:
        future.set_exception(ex)
    else:
        future.set_result(result)


def _bootstrap() -> Dict[str, str]:
    return {"ewoksorange": importlib.metadata.version("ewoksorange")}
