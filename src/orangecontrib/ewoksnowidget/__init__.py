from typing import Tuple

from ewokscore import Task
from ewokscore import TaskWithProgress
from ewoksutils.import_utils import qualname

from ewoksorange.gui.owwidgets import registration
from ewoksorange.gui.owwidgets.base import OWEwoksBaseWidget
from ewoksorange.gui.owwidgets.nothread import OWEwoksWidgetNoThread
from ewoksorange.gui.owwidgets.threaded import OWEwoksWidgetOneThread

from . import widgets

NAME = "No widgets"

DESCRIPTION = "Ewoks tasks without widgets"

LONG_DESCRIPTION = "Widgets for Ewoks tasks that come with a bare Ewoks installation"

ICON = "icons/category.png"

BACKGROUND = "light-blue"

_PROJECT_NAME = "ewoksorange"  # to avoid the "missing addon" error message when opening an ewoks workflow with non-existing widgets

_DEFAULT_WIDGET_CLASSES = dict()


def register_owwidget(widget_class, discovery_object=None):
    package_name = __name__
    category_name = "Ewoks Without Widgets"
    project_name = _PROJECT_NAME

    registration.register_owwidget(
        widget_class,
        package_name,
        category_name,
        project_name,
        discovery_object=discovery_object,
    )


def default_owwidget_class(task_class: Task) -> Tuple[OWEwoksBaseWidget, str]:
    widget_class = _DEFAULT_WIDGET_CLASSES.get(task_class, None)
    if widget_class is not None:
        return widget_class, _PROJECT_NAME

    # Create the widget class
    if issubclass(TaskWithProgress, task_class):
        basecls = OWEwoksWidgetOneThread
    else:
        basecls = OWEwoksWidgetNoThread

    class DefaultOwWidget(basecls, ewokstaskclass=task_class):
        name = qualname(
            task_class
        )  # Allows recreating `DefaultOwWidget` when loading .ows file
        description = f"Orange widget is missing for Ewoks task {task_class.__name__}"
        icon = "icons/nowidget.svg"
        want_main_area = False

        def __init__(self, *args, **kw):
            super().__init__(*args, **kw)
            self._init_control_area()

    widget_class = DefaultOwWidget

    # Add the class to the 'widgets' module
    widget_class.__name__ += "_" + task_class.class_registry_name().replace(".", "_")
    widget_class.__module__ = widgets.__name__
    setattr(widgets, widget_class.__name__, widget_class)

    # Register the widget class
    _DEFAULT_WIDGET_CLASSES[task_class] = widget_class
    register_owwidget(widget_class)
    return widget_class, _PROJECT_NAME


def widget_discovery(discovery):
    for widget_class in _DEFAULT_WIDGET_CLASSES.values():
        register_owwidget(widget_class, discovery_object=discovery)


def global_cleanup_ewoksnowidget():
    """Remove all widget declarations."""
    # Note: the discovery object owns a widget registry which keeps references
    # to all discovered widget classes. The widgets from `ewoksnowidget` are
    # never registered with a global widget registry (so not visible in the
    # widget panel in the canvas) so there is no need to remove the widgets
    # from the registry used during discovery.
    for widget_class in _DEFAULT_WIDGET_CLASSES.values():
        delattr(widgets, widget_class.__name__)
    _DEFAULT_WIDGET_CLASSES.clear()
