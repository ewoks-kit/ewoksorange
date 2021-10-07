import gc
import time
import signal
from typing import Optional
from contextlib import contextmanager
from AnyQt.QtWidgets import QApplication
from AnyQt.QtCore import QEventLoop

APP = None


def ensure_qtapp() -> Optional[QApplication]:
    """Create a Qt application without event loop when no application is running"""
    global APP
    if APP is not None:
        return

    # GUI application
    APP = QApplication.instance()
    if APP is not None:
        return APP

    # Allow termination with CTRL + C
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Application without event loop (APP.exec() is not called)
    APP = QApplication([])
    return APP


def close_qtapp():
    """Close the Qt application created by ensure_qtapp"""
    global APP
    if APP is None:
        return
    APP.processEvents()
    while gc.collect():
        APP.processEvents()
    APP.exit()
    APP = None


@contextmanager
def qtapp_context():
    qtapp = ensure_qtapp()
    try:
        yield qtapp
    finally:
        close_qtapp()


def get_qtapp() -> Optional[QApplication]:
    return QApplication.instance()


def process_qtapp_events():
    """Process all pending Qt events when a Qt event loop is running"""
    global APP
    if APP is None:
        return
    while APP.hasPendingEvents():
        APP.processEvents()


class QtEvent:
    """Event that also works for Qt applications with an event loop
    that need to run manually"""

    def __init__(self):
        self.__flag = False

    def wait(self, timeout=None):
        """Processes events associated to the calling thread while waiting"""
        global APP
        if timeout is not None:
            t0 = time.time()
        while not self.__flag:
            if APP is None:
                time.sleep(0.1)
            else:
                APP.processEvents(QEventLoop.AllEvents, 100)
            if timeout is not None:
                secs = time.time() - t0
                if secs <= 0:
                    return False
        return True

    def set(self):
        self.__flag = True

    def clear(self):
        self.__flag = False


def get_all_qtwidgets():
    app = get_qtapp()
    if app is None:
        return list()

    sapp = str(type(app))
    if "PyQt5" in sapp:
        from PyQt5.sip import ispycreated as createdByPython  # noqa
    elif "PySide2" in sapp:
        from PySide2.shiboken2 import createdByPython  # noqa
    else:
        raise RuntimeError(f"'{sapp}' not supported")

    return [widget for widget in app.allWidgets() if createdByPython(widget)]
