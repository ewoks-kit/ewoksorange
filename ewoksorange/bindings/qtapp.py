import sys
import signal

APP = None


def ensure_qtapp():
    global APP
    if APP is not None:
        return

    from AnyQt.QtWidgets import QApplication

    # Allow termination with CTRL + C
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    APP = QApplication(sys.argv)
