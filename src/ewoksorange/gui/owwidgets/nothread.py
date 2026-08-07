"""
Synchronous (no-thread) Ewoks widget implementation.
"""

from ..concurrency.executor import Concurrency
from .base import OWEwoksBaseWidget
from .meta import ow_build_opts


class OWEwoksWidgetNoThread(
    OWEwoksBaseWidget, **ow_build_opts, concurrency=Concurrency.SYNC
):
    """
    Widget that creates and executes an Ewoks Task synchronously on the main thread.

    Use this for lightweight tasks that won't block the UI.
    """
