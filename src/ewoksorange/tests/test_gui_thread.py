import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from AnyQt.QtWidgets import QApplication

from ..gui.qt_utils.gui_thread import call_in_gui_thread


def _current_thread():
    return threading.current_thread()


def _wait(future, timeout=10):
    t0 = time.time()
    while not future.done():
        assert time.time() - t0 < timeout, "timeout"
        QApplication.processEvents()
        time.sleep(0.01)
    return future.result()


def test_call_in_gui_thread_from_gui_thread(ewoksorange_qtapp):
    assert call_in_gui_thread(_current_thread) is threading.main_thread()


def test_call_in_gui_thread_from_worker_thread(ewoksorange_qtapp):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(call_in_gui_thread, _current_thread)
        assert _wait(future) is threading.main_thread()


def test_call_in_gui_thread_exception(ewoksorange_qtapp):
    def fail():
        raise ValueError("in gui thread")

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(call_in_gui_thread, fail)
        with pytest.raises(ValueError, match="in gui thread"):
            _wait(future)


def test_call_in_gui_thread_timeout(ewoksorange_qtapp):
    called = []

    # The GUI thread does not process events: the call cannot be executed
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            call_in_gui_thread, lambda: called.append(True), timeout=0.1
        )
        with pytest.raises(TimeoutError):
            future.result()

    QApplication.processEvents()
    assert not called
