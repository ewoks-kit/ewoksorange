from ._in_process import _InProcessTaskController


class ThreadTaskController(_InProcessTaskController):
    """Controls a task running in another thread."""
