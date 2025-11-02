import warnings

from ..gui.concurrency.base import TaskExecutor  # noqa F401
from ..gui.concurrency.threaded import ThreadedTaskExecutor  # noqa F401

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.concurrency.taskexecutor' module.",
    DeprecationWarning,
    stacklevel=2,
)
