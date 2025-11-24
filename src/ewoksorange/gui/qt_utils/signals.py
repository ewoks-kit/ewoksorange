from contextlib import ExitStack
from contextlib import contextmanager
from typing import Generator

from AnyQt import QtWidgets


@contextmanager
def block_signals(*widgets: QtWidgets.QWidget) -> Generator[None, None, None]:
    """
    Context manager that blocks signals on one or more Qt widgets.

    .. code-block:: python

        with block_signals(widget1, widget2):
            ...
    """
    with ExitStack() as stack:
        for w in widgets:
            old: bool = w.blockSignals(True)
            stack.callback(w.blockSignals, old)
        yield
