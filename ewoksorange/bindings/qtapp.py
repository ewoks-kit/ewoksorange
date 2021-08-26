import time
import signal
from typing import Optional
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
        return

    # Allow termination with CTRL + C
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Application without event loop (APP.exec() is not called)
    APP = QApplication([])
    return APP


class QtEvent:
    """Event that also works for Qt applications without event loop"""

    def __init__(self):
        self.__flag = False

    def wait(self, timeout=None):
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
