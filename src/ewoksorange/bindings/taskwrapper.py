import warnings

from ..gui.workflows.task_wrappers import OWWIDGET_TASKS_GENERATOR

__all__ = ["OWWIDGET_TASKS_GENERATOR"]

warnings.warn(
    f"The '{__name__}' module is deprecated and will be removed in a future release. "
    "Please migrate to the new 'ewoksorange.gui.bridge.task_wrappers' module.",
    DeprecationWarning,
    stacklevel=2,
)
