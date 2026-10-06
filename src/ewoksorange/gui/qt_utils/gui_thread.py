"""Execute code in the Qt GUI thread from any thread."""

import threading
from concurrent.futures import Future
from typing import Any
from typing import Callable
from typing import Optional

from AnyQt.QtCore import QCoreApplication
from AnyQt.QtCore import QObject
from AnyQt.QtCore import Qt
from AnyQt.QtCore import QThread
from AnyQt.QtCore import Signal
from AnyQt.QtCore import Slot

_INVOKER: Optional["_GuiThreadInvoker"] = None
_INVOKER_LOCK = threading.Lock()


class _GuiThreadInvoker(QObject):
    """Lives in the GUI thread: the slot connected to `_request` is executed
    in the GUI thread, regardless of the thread emitting the signal."""

    _request = Signal(object)

    def __init__(self):
        super().__init__()
        self._request.connect(self._execute, Qt.QueuedConnection)

    def submit(self, func: Callable[[], Any]) -> Future:
        future = Future()
        self._request.emit((func, future))
        return future

    # A real Qt slot: PyQt would otherwise connect through a proxy object living in
    # the thread that makes the connection instead of the thread of this object.
    @Slot(object)
    def _execute(self, request) -> None:
        func, future = request
        if not future.set_running_or_notify_cancel():
            return
        try:
            result = func()
        except BaseException as e:
            future.set_exception(e)
        else:
            future.set_result(result)


def _get_invoker(app: QCoreApplication) -> _GuiThreadInvoker:
    global _INVOKER
    with _INVOKER_LOCK:
        if _INVOKER is None:
            invoker = _GuiThreadInvoker()
            # Can only be done from the thread the object currently lives in.
            invoker.moveToThread(app.thread())
            invoker.setParent(app)  # destroyed with the application
            invoker.destroyed.connect(_reset_invoker)
            _INVOKER = invoker
        return _INVOKER


def _reset_invoker(*_) -> None:
    global _INVOKER
    with _INVOKER_LOCK:
        _INVOKER = None


def call_in_gui_thread(func: Callable[[], Any], timeout: Optional[float] = None) -> Any:
    """Call `func` in the Qt GUI thread and return its result.

    When called from the GUI thread, `func` is called directly. Otherwise the call
    is queued in the Qt event loop of the GUI thread and this function blocks until
    it is done. The GUI thread must therefore not be blocked waiting on the caller.

    :param func: Callable without arguments.
    :param timeout: Maximum number of seconds to wait, `None` to wait forever.
    :raises RuntimeError: No Qt application exists.
    :raises TimeoutError: `func` did not finish in time. When it did not start
                          yet, it will not be called anymore.
    :return: The result of `func`. Exceptions raised by `func` are re-raised.
    """
    app = QCoreApplication.instance()
    if app is None:
        raise RuntimeError("No Qt application: cannot call in the GUI thread")
    if QThread.currentThread() == app.thread():
        return func()
    future = _get_invoker(app).submit(func)
    try:
        return future.result(timeout=timeout)
    except TimeoutError:
        future.cancel()  # not executed later when it did not start yet
        raise
