from ._in_process import _InProcessTaskController


class SyncTaskController(_InProcessTaskController):
    """Controls a task running on the (blocked) calling thread.

    `request_stop()` only has an effect when called concurrently from another
    thread, since the calling thread is busy running the task.
    """
