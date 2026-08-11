"""
Threaded Ewoks widget implementations.
"""

import warnings

from ..concurrency.executor import Concurrency
from ..concurrency.executor import EwoksExecutor
from ..concurrency.executor import SubmitPolicy
from .base import OWEwoksBaseWidget
from .meta import ow_build_opts


class OWEwoksWidgetOneThread(
    OWEwoksBaseWidget,
    **ow_build_opts,
    concurrency=Concurrency.THREAD,
    max_workers=1,
    submit_policy=SubmitPolicy.DROP_IF_BUSY,
):
    """Single background thread; submissions while busy are dropped."""


class OWEwoksWidgetOneThreadPerRun(
    OWEwoksBaseWidget,
    **ow_build_opts,
    concurrency=Concurrency.THREAD,
    max_workers=None,
    submit_policy=SubmitPolicy.ALWAYS,
):
    """Submits each task to a shared thread pool; multiple runs may overlap."""


class OWEwoksWidgetWithTaskStack(
    OWEwoksBaseWidget,
    **ow_build_opts,
    concurrency=Concurrency.THREAD,
    max_workers=1,
    submit_policy=SubmitPolicy.ALWAYS,
):
    """FIFO queue: tasks are queued and run sequentially in a single thread."""

    @property
    def task_executor_queue(self) -> EwoksExecutor:
        """Alias for :attr:`task_executor` kept for backward compatibility."""
        warnings.warn(
            "'task_executor_queue' is deprecated since 6.0. Replaced by 'task_executor'.",
            DeprecationWarning,
        )

        return self.task_executor
