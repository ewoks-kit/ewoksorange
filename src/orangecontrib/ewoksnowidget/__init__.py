from typing import Tuple
from ewokscore import Task, TaskWithProgress
from ewoksorange.bindings.owwidgets import OWEwoksBaseWidget
from ewoksorange.bindings import OWEwoksWidgetNoThread, OWEwoksWidgetOneThread
from ewoksorange import registration
from . import widgets


NAME = "No widgets"

DESCRIPTION = "Ewoks tasks without widgets"

LONG_DESCRIPTION = "Widgets for Ewoks tasks the come with a bare Ewoks installation"

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
        name = f"DefaultOwWidget({task_class.__name__})"
        description = f"Orange widget is missing for Ewoks task {task_class.__name__}"
        icon = "icons/mywidget.svg"
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
