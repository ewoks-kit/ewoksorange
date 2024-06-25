from contextlib import contextmanager
from AnyQt import QtWidgets


@contextmanager
def block_signals(w: QtWidgets.QWidget):
    old = w.blockSignals(True)
    try:
        yield
    finally:
        w.blockSignals(old)
